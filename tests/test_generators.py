from __future__ import print_function
from __future__ import absolute_import
from ku import generators as gr
from ku import generic as gen
from ku import image_utils as iu
from munch import Munch
import pandas as pd, numpy as np
import pytest

gen_params = Munch(batch_size    = 2,
                   data_path     = 'images',
                   input_shape   = (224,224,3),
                   inputs        = ['filename'],
                   outputs       = ['score'],
                   shuffle       = False,
                   fixed_batches = True)

ids = pd.read_csv('ids.csv', encoding='latin-1')

def test_correct_df_input():
    assert (np.all(ids.columns == ['filename', 'score']))
    assert (np.all(ids.score == range(1,5)))

def test_init_DataGeneratorDisk():          
    g = gr.DataGeneratorDisk(ids, **gen_params)
    assert isinstance(g[0], tuple)
    assert isinstance(g[0][0], list)
    assert isinstance(g[0][1], list)
    assert (gen.get_sizes(g[0]) == '([array<2,224,224,3>], [array<2,1>])')
    assert (np.all(g[0][1][0] == np.array([[1],[2]])))
    
def test_read_fn_DataGeneratorDisk():
    import os
    def read_fn(name, g):
        # g is the parent generator object
        # name is the image name read from the DataFrame
        image_path = os.path.join(g.data_path, name)
        return iu.resize_image(iu.read_image(image_path), (100,100))        
        
    g = gr.DataGeneratorDisk(ids, read_fn=read_fn, **gen_params)
    gen.get_sizes(g[0]) =='([array<2,100,100,3>], [array<2,1>])'

def test_process_args_DataGeneratorDisk():
    def preproc(im, arg):
        return np.zeros(1) + arg

    gen_params_local = gen_params.copy()
    gen_params_local.process_fn   = preproc
    gen_params_local.process_args = {'filename': 'filename_args'}
    gen_params_local.batch_size   = 4

    ids_local = ids.copy()
    ids_local['filename_args'] = range(len(ids_local))

    g = gr.DataGeneratorDisk(ids_local, **gen_params_local)
    x = g[0][0]
    assert np.array_equal(np.squeeze(x[0].T), np.arange(gen_params_local.batch_size))

    
def test_get_sizes():
    x = np.array([[1,2,3]])
    assert gen.get_sizes(([x.T],1,[4,5])) == '([array<3,1>], <1>, [<1>, <1>])'
    assert gen.get_sizes(np.array([[1,[1,2]]])) == 'array<1,2>'

def test_DataGeneratorDisk():        
    g = gr.DataGeneratorDisk(ids, **gen_params)
    
    g.inputs = ['filename', 'filename']
    assert gen.get_sizes(g[0]) == '([array<2,224,224,3>, array<2,224,224,3>], [array<2,1>])'

    g.inputs_df = ['score', 'score']
    g.inputs = []
    g.outputs = []
    assert gen.get_sizes(g[0]) == '([array<2,2>], [])'

    g.inputs_df = [['score'], ('score','score')]
    assert gen.get_sizes(g[0]) == '([array<2,1>, array<2,2>], [])'

    g.inputs_df = []
    g.outputs = ['score']
    assert gen.get_sizes(g[0]) == '([], [array<2,1>])'

    g.outputs = ['score',['score']]
    with pytest.raises(AssertionError): g[0]

    g.outputs = [['score'],['score']]
    assert gen.get_sizes(g[0]) == '([], [array<2,1>, array<2,1>])'

def test_H5Reader_and_Writer():
    with gen.H5Helper('data.h5', overwrite=True) as h:
        data = np.expand_dims(np.array(ids.score), 1)
        h.write_data(data, list(ids.filename))

    with gen.H5Helper('data.h5', 'r') as h:
        data = h.read_data(list(ids.filename))
        assert all(data == np.array([[1],[2],[3],[4]]))
        
def test_DataGeneratorHDF5():
    gen_params_local = gen_params.copy()
    gen_params_local.update(data_path='data.h5', inputs=['filename'])    
    g = gr.DataGeneratorHDF5(ids, **gen_params_local)
    
    assert gen.get_sizes(g[0]) == '([array<2,1>], [array<2,1>])'
    
    g.inputs_df = ['score', 'score']
    g.inputs = []
    g.outputs = []
    assert gen.get_sizes(g[0]) == '([array<2,2>], [])'

    g.inputs_df = [['score'], ('score','score')]
    assert gen.get_sizes(g[0]) == '([array<2,1>, array<2,2>], [])'

    g.inputs_df = []
    g.outputs = ['score']
    assert gen.get_sizes(g[0]) == '([], [array<2,1>])'

    g.outputs = ['score',['score']]
    with pytest.raises(AssertionError): g[0]

    g.outputs = [['score'],['score']]
    assert gen.get_sizes(g[0]) == '([], [array<2,1>, array<2,1>])'
    
def test_DataGeneratorHDF5_callable_outputs():
    d = {'features': [1, 2, 3, 4, 5],
         'mask': [1, 0, 1, 1, 0]}
    df = pd.DataFrame(data=d)

    def filter_features(df):
        return np.array(df.loc[df['mask']==1,['features']])

    gen_params.update(data_path = None, 
                      outputs   = filter_features,
                      inputs    = [],
                      inputs_df = ['features'],
                      shuffle   = False,
                      batch_size= 5)

    g = gr.DataGeneratorHDF5(df, **gen_params)
    assert gen.get_sizes(g[0]) == '([array<5,1>], array<3,1>)'
    assert all(np.squeeze(g[0][0]) == np.arange(1,6))
    assert all(np.squeeze(g[0][1]) == [1,3,4])