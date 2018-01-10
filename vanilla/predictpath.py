#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##################################################
# predictpath.py
# AS path prediction for given client and guard sets
# Input:
# List of Tor client ASes (--client_file, default="data/top400client.txt")
# List of Tor guard ASes (--guard_as_file, default="data/as_guard.txt")
# CAIDA AS topology (--topology_file, default="data/20161001.as-rel2.txt")
# Output:
# Predicted paths between clients and guards (data/cg_path.json)
##################################################

import sys
import json
from collections import deque
import time
import argparse


# use BFS to traverse the graph given a destination
# graph[source] = [type,path1,path2], in which type is 0 (p-c), 1 (p-p), or 2 (c-p)

# initialize graph
def init(root):
    global graph
    graph = {}
    graph[root] = [0,[root]]

def bfs_cp(root):
    global graph, asdict
    q = deque([root])
    while q:
        current = q.popleft()
        cur_len = len(graph[current][1])
        cur_path = graph[current][1:]
        for node in asdict[current][2]:
            if node in graph:
                path_len = len(graph[node][1])
                if path_len == (cur_len + 1):
                    for each in cur_path:
                        newpath = [node] + each
                        graph[node].append(newpath)
                elif path_len > (cur_len + 1):
                    print("we have problem for cur node %s and its cp node %s" % (current,node))
                else:
                    pass
            else:
                graph[node] = [0]
                for each in cur_path:
                    newpath = [node] + each
                    graph[node].append(newpath)
                q.append(node)
    # sanity check
    for n in graph:
        len_lst = [len(x) for x in graph[n][1:]]
        if len(set(len_lst)) != 1:
            print("we have a problem in customer-provider")
            print(n)
            print(graph[n])

def bfs_pp(q_lst):
    global graph, asdict
    for current in q_lst:
        cur_len = len(graph[current][1])
        cur_path = graph[current][1:]
        for node in asdict[current][1]:
            if node in graph:
                path_type = graph[node][0]
                path_len = len(graph[node][1])
                if path_type == 1 and path_len == (cur_len + 1):
                    for each in cur_path:
                        newpath = [node] + each
                        graph[node].append(newpath)
                elif path_type == 1 and path_len > (cur_len + 1):
                    graph[node] = [1]
                    for each in cur_path:
                        newpath = [node] + each
                        graph[node].append(newpath)
                else:
                    pass
            else:
                graph[node] = [1]
                for each in cur_path:
                    newpath = [node] + each
                    graph[node].append(newpath)
    # sanity check
    for n in graph:
        len_lst = [len(x) for x in graph[n][1:]]
        if len(set(len_lst)) != 1:
            print("we have a problem in peer-peer")
            print(n)
            print(graph[n])

def bfs_pc(q_lst):
    global graph, asdict
    q = deque(q_lst)
    while q:
        current = q.popleft()
        cur_len = len(graph[current][1])
        cur_path = graph[current][1:]
        for node in asdict[current][0]:
            if node in graph:
                path_type = graph[node][0]
                path_len = len(graph[node][1])
                if path_type == 2 and path_len == (cur_len + 1):
                    for each in cur_path:
                        newpath = [node] + each
                        graph[node].append(newpath)
                elif path_type == 2 and path_len > (cur_len + 1):
                    graph[node] = [2]
                    for each in cur_path:
                        newpath = [node] + each
                        graph[node].append(newpath)
                else:
                    pass
            else:
                graph[node] = [2]
                for each in cur_path:
                    newpath = [node] + each
                    graph[node].append(newpath)
                q.append(node)

    # sanity check
    for n in graph:
        len_lst = [len(x) for x in graph[n][1:]]
        if len(set(len_lst)) != 1:
            print("we have a problem in provider-customer")
            print(n)
            print(graph[n])

def getPath(lst,sdex):
    tmplst = [int(x[sdex]) for x in lst]
    minasn = min(tmplst)
    newlst = []
    for l in lst:
        if int(l[sdex]) == minasn:
            newlst.append(l)
    if len(newlst) > 1:
        return getPath(newlst,sdex+1)
    else:
        return newlst[0]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology_file",
                        default="data/20161001.as-rel2.txt")
    parser.add_argument("--client_file",
                        default="data/top400client.txt")
    parser.add_argument("--guard_as_file",
                        default="data/as_guard.txt")
    parser.add_argument("--notiebreak", action="store_true")
    return parser.parse_args()

def main(args):
    global asdict, graph
    asdict = {}

    # load AS relationships from CAIDA topo file
    # asdict[asn] = [[provider-customer edges],[peer-to-peer edges],[customer-provider edges]]
    for line in open(args.topology_file):
        if not line.strip().startswith("#"):
            arr = line.strip().split('|')
            asn1 = arr[0]
            asn2 = arr[1]
            rel = int(arr[2]) # -1: provider-customer; 0: peer-to-peer
            if asn1 in asdict:
                asdict[asn1][rel+1].append(asn2)
            else:
                asdict[asn1] = [[],[],[]]
                asdict[asn1][rel+1] = [asn2]
            if asn2 in asdict:
                asdict[asn2][abs(rel)+1].append(asn1)
            else:
                asdict[asn2] = [[],[],[]]
                asdict[asn2][abs(rel)+1] = [asn1]

    client_dict = {}
    g_lst = []

    for line in open(args.client_file):
        if line.strip() in asdict:
            client_dict[line.strip()] = {}
        else:
            print("%s not found in topology" % line.strip())

    for line in open(args.guard_as_file):
        g_lst.append(line.strip())
        for cl in client_dict:
            client_dict[cl][line.strip()] = [[],[]] #[forward,reverse]

    print("input file loading done. start forward path calculation now.")

    # format
    # {client: {guard: [[path1,path2],[path1,path2]]}} in which guard:[forward,reverse]
    # {dest: {exit: [[path1,path2],[path1,path2]]}} in which exit:[forward,reverse]

    start = time.time()

    # first, we do forward: guard is the destination, and client is the source
    for item in g_lst:
        init(item)
        bfs_cp(item)
        bfs_pp(list(graph.keys()))
        bfs_pc(list(graph.keys()))
        # now, find the client sources
        for cl in list(client_dict.keys()):
            if cl in graph:
                client_dict[cl][item][0] = graph[cl][1:]
            else:
                print("forward path not found from client %s to guard %s" % (cl,item))

    end = time.time()
    print("forward calculation finished")
    print(end - start)

    # second, we do reverse: client is the destination, guard is the source
    for cl in list(client_dict.keys()):
        init(cl)
        bfs_cp(cl)
        bfs_pp(list(graph.keys()))
        bfs_pc(list(graph.keys()))
        # now, find the guards
        for item in g_lst:
            if item in graph:
                client_dict[cl][item][1] = graph[item][1:]
            else:
                print("reverse path not found from guard %s to client %s" % (item,cl))

    end = time.time()
    print("reverse calculation finished")
    print(end - start)

    # Format: client: {guard: [forpath, revpath]}
    if not args.notiebreak:
        print("performing tiebreak by router ID")
        toberemoved = []
        for cl in client_dict:
            ifcomplete = True
            for g in client_dict[cl]:
                flst = client_dict[cl][g][0]
                rlst = client_dict[cl][g][1]
                if flst and rlst:
                    newf = getPath(flst,0)
                    newr = getPath(rlst,0)
                    client_dict[cl][g] = [newf,newr]
                else:
                    ifcomplete = False
                    break
            if not ifcomplete:
                toberemoved.append(cl)
        print(toberemoved)
        for c in toberemoved:
            client_dict.pop(c,None)

    with open('data/cg_path.json','w+') as fp:
        json.dump(client_dict,fp)


if __name__ == '__main__':
    main(parse_args())

