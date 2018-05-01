#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
# Copyright (C) 2018 Chunheng Jiang (jiangchunheng@gmail.com)
# Created at 12:58 AM Mar 26, 2018

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from sklearn.mixture import GMM
import networkx as nx


def authorship():
    authship = pd.read_csv('authorship.csv')
    B = nx.Graph()
    B.add_nodes_from(authship['author'], bipartite=0)
    B.add_nodes_from(authship['article'], bipartite=1)

    for i in range(authship.shape[0]):
        record = authship.iloc[i]
        B.add_node((record['author'], record['article']))

    # Separate by group
    l, r = nx.bipartite.sets(B)
    pos = {}

    # Update position for node from each group
    pos.update((node, (1, index)) for index, node in enumerate(l))
    pos.update((node, (2, index)) for index, node in enumerate(r))

    nx.draw(B, pos=pos)
    plt.show()


if __name__ == '__main__':
    authorship()
