#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 2:40 PM Feb 27, 2018

import os
import pickle

import numpy as np
import pandas as pd

from numpy.linalg import pinv

from datautil import CitNet, CitNode

import networkx as nx


class Shen(object):
    """
    Shen's method to compute the collective credit for coauthors
    """

    def __init__(self):
        with open('citnodes.db', 'rb') as fd:
            self.nodes = pickle.load(fd)

    def allocate(self, ind):
        node = self.nodes[ind]
        authors = node.authors
        if len(authors) == 1:
            return authors, [1.0]

        citations = node.citations

        cooccurence = []
        for c in citations:
            refs = self.nodes[c].references
            cooccurence += list(refs)

        count_cooccurence = {x: cooccurence.count(x) for x in cooccurence}
        cocited = set(cooccurence)
        strengths = np.array([count_cooccurence[k] for k in cocited])

        creds_mat = np.array(self.get_credit_allocation_mat(authors, cocited))
        creds = np.matmul(strengths, creds_mat)
        return authors, creds / sum(creds)

    def get_credit_allocation_mat(self, authors, cocited):
        mat = []
        for cc in cocited:
            cocited_authors = set(self.nodes[cc].authors)
            ratio_credit = 1.0 / len(cocited_authors)
            creds = [ratio_credit if auth in cocited_authors else 0 for auth in authors]
            mat.append(creds)
        return mat


class SimpleImportanceBased(Shen):
    """
    The quality of the citing papers determine the credibility of the selected committee (cocited
    articles). Each citing document is assigned an importance score.
    The importance score is appropriate to the number of citations the document earned in the
    community.
    """

    def allocate(self, ind):
        node = self.nodes[ind]
        authors = node.authors
        if len(authors) == 1:
            return authors, [1.0]

        citations = node.citations

        total_scores = 0
        importances = dict()
        for c in citations:
            refs = self.nodes[c].references
            score = len(self.nodes[c].citations)
            for ref in refs:
                if ref in importances:
                    importances[ref] += score
                else:
                    importances[ref] = score
            total_scores += score

        cocited = set(importances.keys())
        strengths = np.array([importances[c] / total_scores for c in cocited])

        creds_mat = np.array(self.get_credit_allocation_mat(authors, cocited))
        creds = np.matmul(strengths, creds_mat)
        return authors, creds / sum(creds)


class PRImportanceBased(Shen):
    """
    The quality of the citing papers determine the credibility of the selected committee (cocited
    articles). Each citing document is assigned an importance score. The importance score is
    appropriate to the PageRank score the document earned in the community.
    """

    def __init__(self):
        super(PRImportanceBased, self).__init__()
        self.scores = pd.read_csv('pagerank.csv')

    def allocate(self, ind):
        node = self.nodes[ind]
        authors = node.authors
        if len(authors) == 1:
            return authors, [1.0]

        citations = node.citations

        total_scores = 0
        importances = dict()
        for c in citations:
            refs = self.nodes[c].references
            score = float(self.scores[self.scores.i == c].pr)
            for ref in refs:
                if ref in importances:
                    importances[ref] += score
                else:
                    importances[ref] = score
            total_scores += score

        cocited = set(importances.keys())
        strengths = np.array([importances[c] / total_scores for c in cocited])

        creds_mat = np.array(self.get_credit_allocation_mat(authors, cocited))
        creds = np.matmul(strengths, creds_mat)
        return authors, creds / sum(creds)


class IntrinsicCredit():
    def __init__(self):
        with open('citnodes.db', 'rb') as fd:
            self.nodes = pickle.load(fd)

        authors = pd.read_csv('authors.csv')
        self.m = len(self.nodes)
        self.n = authors.shape[0]

        # credit, indicator, strength matrices
        self.C = np.zeros((self.n, self.m))
        self.B = np.ones((self.n, self.m))
        self.S = np.zeros((self.m, self.m))

    def build_matrices(self):
        for i in range(self.m):
            node = self.nodes[i]
            authors = node.authors
            if authors:
                cred = 1.0 / len(authors)
                for a in authors:
                    self.B[a][i] = 0
                    self.C[a][i] = cred

            citations = node.citations
            cooccurence = []
            for c in citations:
                refs = self.nodes[c].references
                cooccurence += list(refs)

            cocited = set(cooccurence)
            for k in cocited:
                self.S[k][i] = cooccurence.count(k)

    def compute(self, exact=True, alpha=0.1, num_iter=100, epsilon=1.0e-10):
        self.build_matrices()

        d = self.S - np.identity(self.m)
        ddt = np.matmul(d, np.matrix.transpose(d))
        if exact:
            creds = -np.matmul(self.B, pinv(ddt))
            with open('credit.db', 'wb') as fd:
                pickle.dump(creds, fd)


if __name__ == '__main__':
    print('')

    articles = pd.read_csv('articles.csv', usecols=['id', 'doi'])
    authors = pd.read_csv('authors.csv')

    algo = Shen()
    # algo = SimpleImportanceBased()
    # algo = PRImportanceBased()

    awardings = pd.read_csv('nobel.csv')
    fmt = '{0},{1},{2},{3},{4}\n'
    with open('alloc.csv', 'a+') as file:
        file.write('id,article,author,credit,nobelwinner\n')
        for k, row in awardings.iterrows():
            print(row.article)
            id = int(row.id)
            auth_indices, credits = algo.allocate(id)
            for i in range(len(auth_indices)):
                auth = auth_indices[i]
                found = authors[authors['id'] == auth]
                name = found['name'].values[0]
                nobel = found['nobelwinner'].values[0]
                file.write(fmt.format(id, row.article, name, credits[i], nobel))
