#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 5:59 PM Mar 20, 2018

import xmltodict

import pickle

import pandas as pd
from collections import OrderedDict

DATABASE = '/Users/chjiang/GitHub/data/aps/'


class Author(object):
    def __init__(self, given, middle, surname):
        self.given = given
        self.middle = middle
        self.surname = surname
        self.id = -1

    def __str__(self):
        nms = self.features()
        return ' '.join(nms)

    def __hash__(self):
        nms = self.features()
        return hash((nms[0], nms[1], nms[2]))

    def features(self):
        f = []
        if self.given:
            f.append(self.given[0].title())
        else:
            f.append('')
        if self.middle:
            f.append(self.middle[0].title())
        else:
            f.append('')

        if self.surname:
            f.append(self.surname.title())
        else:
            f.append('')
        return f

    def __eq__(self, other):
        return self.features() == other.features()


class CitNet(object):
    def __init__(self):
        self.authorship = []
        self.authbook = dict()
        self.authtable = []
        self.file_cit_net = DATABASE + 'citing_cited.csv'

    def parse_aps(self):
        journals = 'PR,PRA,PRB,PRC,PRD,PRE,PRI,PRL,PRSTAB,PRSTPER,RMP'.split(',')
        num_articles, num_authors = 0, 0
        with open('articles2.csv', 'w+') as ostream:
            ostream.write('id,doi,journal,numauth\n')

            for journal in journals:
                xml = DATABASE + journal + '.xml'
                file = open(xml)
                doc = xmltodict.parse(file.read())
                entries = doc['articles']['article']
                for entry in entries:
                    doi = entry['doi']

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

                        names = self.sort_out_names(names)
                        noname = sum([1 for name in names if name == ''])
                        if noname == len(names):
                            continue

                        author = Author(*names)
                        if author in self.authbook:
                            ind = self.authbook[author]
                            authgroup.append(self.authtable[ind])
                            continue

                        author.id = num_authors
                        authgroup.append(author)
                        self.authtable.append(author)
                        self.authbook[author] = num_authors
                        num_authors += 1

                    if not authgroup:
                        continue

                    print(num_articles, journal)
                    printdate = ''
                    if 'issue' in entry:
                        printdate = entry['issue']['printdate']
                        len = len(printdate)
                        if len > 4 and '-' in printdate:
                            ind = printdate.index('-')
                            printdate = printdate[:ind]
                    ostream.write('{0},{1},{2},{3},{4}\n'.format(num_articles, doi, printdate, journal, len(authgroup)))

                    # recording the authorship
                    for author in authgroup:
                        self.authorship.append([num_articles, author.id])
                    num_articles += 1
                file.close()

        # self.dump_authors()
        # self.dump_authorship()

    def sort_out_names(self, names):
        if names[2] == 'Jr.':
            names[2] = names[1] + ' Jr.'
            names[1] = names[0]
            names[0] = ''
        elif names[0] == 'and':
            names[0] = ''
        elif names[2] == 'and':
            names[1] = ''
            names[2] = names[1]

        for i in range(len(names)):
            name = names[i]
            if name:
                name = ''.join([_ for _ in name if not _.isdigit()])
                name = name.replace('†', '').replace('@f', '')
                name = name.replace(',', ' ').strip()
                names[i] = ' '.join(name.split())
        return names

    def dump_authors(self):
        with open('authors.csv', 'w+') as file:
            file.write('id,given,middle,surname,name\n')
            fmt = '{0},{1},{2},{3},{4}\n'
            for author in self.authbook.keys():
                line = fmt.format(author.id, author.given, author.middle, author.surname, str(author))
                file.write(line)

    def dump_authorship(self):
        with open('authorship.csv', 'w+') as file:
            file.write('article,author\n')
            for article, author in self.authorship:
                file.write('{0},{1}\n'.format(article, author))

    def parse_nodes(self):
        articles = pd.read_csv('articles.csv', usecols=['id', 'doi'])
        indicies_doi = dict(zip(articles.doi, articles.id))

        net = pd.read_csv(self.file_cit_net)
        references = dict(net.groupby('citing_doi')['cited_doi'].apply(list))
        citations = dict(net.groupby('cited_doi')['citing_doi'].apply(list))

        authorship = pd.read_csv('authorship.csv')
        authors = dict(authorship.groupby('article')['author'].apply(list))

        nodes = {}
        for i in range(articles.shape[0]):
            article = articles.iloc[i]
            node = CitNode()
            doi = article.doi
            node.authors = authors[article.id]
            if doi in references:
                node.references = set([indicies_doi[r] for r in references[doi] if r in indicies_doi])
            if doi in citations:
                node.citations = set([indicies_doi[c] for c in citations[doi] if c in indicies_doi])
            nodes[indicies_doi[doi]] = node

        with open('citnodes.db', 'wb') as fd:
            pickle.dump(nodes, fd)


class CitNode(object):
    def __init__(self):
        self.authors = []
        self.references = set()
        self.citations = set()


def citnet():
    with open('citnodes.db', 'rb') as fd:
        nodes = pickle.load(fd)

        with open('citnet2.csv', 'a') as file:
            file.write('Source,Target\n')
            for citing in nodes.keys():
                cited = nodes[citing].references

                entries = [str(citing) + ',' + str(c) for c in cited]
                lines = '\n'.join(entries) + '\n'
                file.write(lines)


if __name__ == '__main__':
    citnet = CitNet()
    citnet.parse_aps()
    # citnet.parse_nodes()
    # citnet()
