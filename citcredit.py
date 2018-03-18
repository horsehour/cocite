#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 2:40 PM Feb 27, 2018

import xmltodict

import os
import pickle

import numpy as np
import pandas as pd
from collections import OrderedDict


class Article(object):
    def __init__(self, title):
        self.title = title

        self.doi = ''
        self.id = -1

        self.authors = None

    def __lt__(self, other):
        return self.doi.__lt__(other.doi)


class Author(object):
    def __init__(self, given, middle, surname, corresponding=False):
        self.given = given
        self.middle = middle
        self.surname = surname
        self.corresponding = corresponding
        self.id = -1

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        names = [self.given, self.middle, self.surname]
        return ' '.join(names)


class CitNet(object):
    def __init__(self):
        self.articles = []
        self.authors = []
        self.dois = None
        self.file_cit_net = 'APS/citing_cited.csv'

    def get_aps_cit_net(self):
        if not os.path.exists('doi.db'):
            net = pd.read_csv(self.file_cit_net)
            ref = set(net['citing_doi'])
            cit = set(net['cited_doi'])
            self.dois = sorted(ref.union(cit))
        else:
            with open('doi.db', 'rb') as file:
                self.dois = pickle.load(file)

    def parse_aps(self):
        self.get_aps_cit_net()

        journals = 'PR,PRA,PRB,PRC,PRD,PRE,PRI,PRL,PRSTAB,PRSTPER,RMP'.split(',')
        authorset = set()

        num_articles, num_authors = 0, 0
        for journal in journals:
            xml = 'APS/' + journal + '.xml'
            # xml = 'exception.xml'

            file = open(xml)
            doc = xmltodict.parse(file.read())
            entries = doc['articles']['article']
            for entry in entries:
                article = Article(entry['title'])
                print(num_articles, journal, article.title)

                article.doi = entry['@doi']
                article.id = num_articles
                num_articles += 1

                authgroup = []

                # no author
                if 'authgrp' not in entry:
                    continue

                group = []
                if isinstance(entry['authgrp'], list):
                    for g in entry['authgrp']:
                        if 'author' not in g:
                            continue

                        if isinstance(g['author'], OrderedDict):
                            group.append(g['author'])
                        elif isinstance(g['author'], list):
                            for c in g['author']:
                                group.append(c)
                elif isinstance(entry['authgrp'], OrderedDict):
                    if 'author' not in entry['authgrp']:
                        continue

                    auth = entry['authgrp']['author']
                    if isinstance(auth, OrderedDict):
                        group.append(auth)
                    elif isinstance(auth, list):
                        for a in auth:
                            group.append(a)

                for auth in group:
                    names = ['givenname', 'middlename', 'surname']
                    for i in range(len(names)):
                        name = names[i]
                        if name in auth:
                            name = auth[name]
                            if not name:
                                names[i] = ''
                            elif isinstance(name, list):  # name may be a list
                                name = [n for n in name if n is not None]
                                names[i] = ' '.join(name)
                            else:
                                names[i] = name
                        else:
                            names[i] = ''

                    author = Author(*names)
                    authgroup.append(author)

                    if author in authorset:
                        continue
                    else:
                        self.authors.append(author)
                        author.id = num_authors
                        authorset.add(author)
                        num_authors += 1
                article.authors = authgroup
                self.articles.append(article)
            file.close()

        with open('authors.db', 'wb') as fd:
            pickle.dump(self.authors, fd)

        with open('articles.db', 'wb') as fd:
            pickle.dump(self.articles, fd)

        with open('doi.db', 'wb') as fd:
            pickle.dump(self.dois, fd)

    def parse_nodes(self):
        net = pd.read_csv(self.file_cit_net)

        with open('articles.db', 'rb') as file:
            articles = pickle.load(file)

        indicies_doi = {}
        for article in articles:
            indicies_doi[article.doi] = article.id

        nodes = {}
        for article in articles:
            node = CitNode()
            doi = article.doi
            node.authors = [auth.id for auth in article.authors]
            ref = net[net['citing_doi'] == doi]['cited_doi']
            for r in list(ref):
                if r not in indicies_doi:
                    continue
                node.references.add(indicies_doi[r])

            cit = net[net['cited_doi'] == doi]['citing_doi']
            node.citations = set()
            for c in list(cit):
                if c not in indicies_doi:
                    continue
                node.citations.add(indicies_doi[c])
            nodes[indicies_doi[doi]] = node
        return nodes


class CitNode(object):
    def __init__(self):
        self.authors = []
        self.references = set()
        self.citations = set()


class Shen(object):
    """
    Shen's method to compute the collective credit for coauthors
    """

    def __init__(self):
        citnet = CitNet()
        self.nodes = citnet.parse_nodes()

    def allocate(self, ind):
        node = self.nodes[ind]
        authors = node.authors
        citations = node.citations
        references = []
        cocited = set()
        for c in citations:
            references.append(self.nodes[c].references)
            cocited = cocited.union(references)
        cocited.add(ind)
        strengths = np.array(self.get_strengths(cocited, references))
        creds_mat = np.array(self.get_credit_allocation_mat(authors, cocited))
        creds = np.matmul(strengths, creds_mat)
        return creds

    def get_strengths(self, cocited, references):
        strengths = []
        for cc in cocited:
            s = 0
            for ref in references:
                if cc in ref:
                    s += 1
            strengths.append(s)
        return strengths

    def get_credit_allocation_mat(self, authors, cocited):
        mat = []
        for cc in cocited:
            cocited_authors = set(self.nodes[cc].authors)
            unit_credit = 1.0 / len(cocited_authors)
            creds = [0] * len(authors)
            for i in range(len(authors)):
                author = authors[i]
                if author in cocited_authors:
                    creds[i] = unit_credit
                else:
                    creds[i] = 0
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

    algo = Shen()
    print(algo.allocate(0))
