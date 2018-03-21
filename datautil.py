#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 5:59 PM Mar 20, 2018

import xmltodict

import os
import pickle

import numpy as np
import pandas as pd
from collections import OrderedDict

DATABASE = '/Users/chjiang/GitHub/data/aps/'


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

    def name(self):
        nms = []
        if self.given:
            nms.append(self.given)
        if self.middle:
            nms.append(self.middle)
        if self.surname:
            nms.append(self.surname)
        return ' '.join(nms)


class CitNet(object):
    def __init__(self):
        self.articles = []
        self.authors = []
        self.dois = None
        self.file_cit_net = DATABASE + 'citing_cited.csv'

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
            xml = DATABASE + journal + '.xml'

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

        references = dict(net.groupby('citing_doi')['cited_doi'].apply(list))
        citations = dict(net.groupby('cited_doi')['citing_doi'].apply(list))

        nodes = {}
        for article in articles:
            node = CitNode()
            doi = article.doi
            node.authors = [auth.id for auth in article.authors]
            if doi in references:
                node.references = set([indicies_doi[r] for r in references[doi] if r in indicies_doi])
            if doi in citations:
                node.citations = set([indicies_doi[c] for c in citations[doi] if c in indicies_doi])
            nodes[indicies_doi[doi]] = node
        return nodes


class CitNode(object):
    def __init__(self):
        self.authors = []
        self.references = set()
        self.citations = set()


def index_doi():
    with open('articles.db', 'rb') as file:
        articles = pickle.load(file)

    indicies_doi = {}
    for article in articles:
        indicies_doi[article.doi] = article.id

    with open('doi.ind', 'wb') as file:
        pickle.dump(indicies_doi, file)


def inv_index_author():
    inv_indices = dict()
    with open('authors.db', 'rb') as file:
        authors = pickle.load(file)
        for author in authors:
            inv_indices[author.id] = author.name()

    with open('inv.auth.ind', 'wb') as file:
        pickle.dump(inv_indices, file)


if __name__ == '__main__':
    # index_doi()
    inv_index_author()
