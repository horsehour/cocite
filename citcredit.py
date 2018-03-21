#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 2:40 PM Feb 27, 2018

import os
import pickle

import numpy as np
import pandas as pd

from datautil import CitNet, CitNode


class Shen(object):
    """
    Shen's method to compute the collective credit for coauthors
    """

    def __init__(self):
        citnet = CitNet()

        if os.path.exists('citnodes.db'):
            with open('citnodes.db', 'rb') as fd:
                self.nodes = pickle.load(fd)
        else:
            self.nodes = citnet.parse_nodes()
            with open('citnodes.db', 'wb') as fd:
                pickle.dump(self.nodes, fd)

    def allocate(self, ind):
        node = self.nodes[ind]
        authors = node.authors
        citations = node.citations

        cooccurence = []
        references = []
        for c in citations:
            refs = self.nodes[c].references
            references.append(refs)
            cooccurence += list(refs)

        count_cooccurence = {x: cooccurence.count(x) for x in cooccurence}
        count_cooccurence[ind] = len(citations)

        cocited = set().union(*references)
        cocited.add(ind)

        strengths = np.array([count_cooccurence[k] for k in cocited])

        creds_mat = np.array(self.get_credit_allocation_mat(authors, cocited))
        creds = np.matmul(strengths, creds_mat)
        return authors, creds

    def get_credit_allocation_mat(self, authors, cocited):
        num_auth = len(authors)

        mat = []
        for cc in cocited:
            cocited_authors = set(self.nodes[cc].authors)
            ratio_credit = 1.0 / len(cocited_authors)
            creds = [ratio_credit if authors[i] in cocited else 0 for i in range(num_auth)]
            mat.append(creds)
        return mat


class ModifiedShen(Shen):
    """
    A modification over Shen's algorithm
    """


if __name__ == '__main__':
    print('')

    # algo = CitNet()
    # algo.parse_aps()

    # doi indexing table
    with open('doi.ind', 'rb') as file:
        ind = pickle.load(file)

    with open('auth.inv.ind', 'rb') as file:
        inv_ind = pickle.load(file)

    algo = Shen()
    articles = list(pd.read_csv('nobelarticles.csv')['article'])
    for doi in articles:
        id = ind[doi]
        aids, cids = algo.allocate(id)
        print(doi)
        for i in range(len(aids)):
            aid = aids[i]
            print('{0} : {1}'.format(inv_ind[aid], cids[i]))

