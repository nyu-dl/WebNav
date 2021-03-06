'''
Custom theano class to access page links.
'''

import numpy as np
import theano
from theano import gof
from theano import tensor
import time
import parameters as prm
import utils

class Link(theano.Op):
    __props__ = ()

    def __init__(self, wiki, wikipre, vocab):
        self.wiki = wiki
        self.wikipre = wikipre
        self.vocab = vocab
        self.mem = {}

    def make_node(self, x, x2, x3, x4, x5):
        # check that the theano version has support for __props__.
        # This next line looks like it has a typo,
        # but it's actually a way to detect the theano version
        # is sufficiently recent to support the use of __props__.
        assert hasattr(self, '_props'), "Your version of theano is too old to support __props__."
        x = tensor.as_tensor_variable(x)
        x2 = tensor.as_tensor_variable(x2)
        x3 = tensor.as_tensor_variable(x3)
        x4 = tensor.as_tensor_variable(x4)
        x5 = tensor.as_tensor_variable(x5)
        
        if prm.att_doc:
            if prm.compute_emb:
                td = tensor.itensor4().type()
            else:
                td = tensor.ftensor4().type()
            tm = tensor.ftensor3().type()
        else:
            if prm.compute_emb:
                td = tensor.itensor3().type()
            else:
                td = tensor.ftensor3().type()
            tm = tensor.fmatrix().type()
        return theano.Apply(self, [x,x2,x3,x4,x5], [td, tm, \
                                           tensor.fmatrix().type(), tensor.ivector().type()])


    def perform(self, node, inputs, output_storage):
        #st = time.time()
        pages_id = inputs[0]
        p_truth = inputs[1]
        it = int(inputs[2])
        uidx = int(inputs[3])
        k_beam = int(inputs[4])

        run = True
        if uidx in self.mem:
            if it in self.mem[uidx]:
                L, L_m, l_page_id, l_truth = self.mem[uidx][it]
                run = False
        
        if run:
            max_links = k_beam
            lst_links = []
            for i, page_id in enumerate(pages_id):
                if int(page_id) != -1:
                    links = self.wiki.get_article_links(page_id)
                    links = list(set(links)) # remove duplicates.
                    links.sort() # h5py only accepts sorted indexes.
                    lst_links.append(links)

                    if len(links) > max_links:
                        max_links = len(links)
                else:
                    lst_links.append([])

            if prm.att_doc:
                if prm.compute_emb:
                    L = np.zeros((len(pages_id), max_links, prm.max_segs_doc, prm.max_words), np.int32)
                else:
                    L = np.zeros((len(pages_id), max_links, prm.max_segs_doc, prm.dim_emb), np.float32)
                L_m = np.zeros((len(pages_id), max_links, prm.max_segs_doc), np.float32)
            else:
                if prm.compute_emb:
                    L = np.zeros((len(pages_id), max_links, prm.max_words), np.int32)
                else:
                    L = np.zeros((len(pages_id), max_links, prm.dim_emb), np.float32)
                L_m = np.zeros((len(pages_id), max_links), np.float32)

            l_page_id = -np.ones((len(pages_id), max_links+1), np.float32) # '+1' to consider stop action.
            l_truth = np.zeros((len(pages_id)), np.int32)

            
            for i, links in enumerate(lst_links):
                if len(links) > 0:
                    if prm.compute_emb:
                        # retrieve the precomputed indexes.
                        links_c = self.wikipre.f['idx'][links]
                    else:
                        # retrieve the precomputed embeddings.
                        links_c = self.wikipre.f['emb'][links]

                    if prm.att_doc:
                        L[i,:len(links),:,:] = links_c
                        links_mask = self.wikipre.f['mask'][links]
                        for k, link_mask in enumerate(links_mask):
                            L_m[i,k,:link_mask] = 1.0
                    else:
                        L[i,:len(links),:] = links_c
                        L_m[i,:len(links)] = 1.0

                    l_page_id[i,1:len(links)+1] = links  # +1 because of the stop action.
                    for k, link_id in enumerate(links):
                        if link_id == p_truth[i]:
                            l_truth[i] = k + 1 # +1 because of the stop action.


            if uidx in self.mem:
                self.mem[uidx][it] = [L, L_m, l_page_id, l_truth]
            else:                
                self.mem = {uidx: {it: [L, L_m, l_page_id, l_truth]}}

        
        output_storage[0][0] = L
        output_storage[1][0] = L_m
        output_storage[2][0] = l_page_id
        output_storage[3][0] = l_truth
        #print 'uidx', uidx, 'it', it, 'time Link op:', str(time.time() - st)

    def grad(self, inputs, output_grads):
        return [tensor.zeros_like(ii, dtype=theano.config.floatX) for ii in inputs]
        
