#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##################################################
# denasa_client_country.py
# compute new percentage of risk-free paths considering mobility
# Input:
# List of Tor client ASes (--client_file, default="data/top400client.txt")
# Tor guard relay bandwidth (--guard_file, default="data/guard_as_bw.json")
# Predicted paths between client and guard (--path_file, default="data/cg_path.json")
# Output:
# New percentages for each client AS ([clientAS].txt)
##################################################


import sys
import json
import argparse
import datetime
import time
from os.path import basename
from collections import defaultdict


def orderClient(filename):
    clientlst = []
    for line in open(filename, 'r'):
        asnum = line.split()[0]
        tsstr = ' '.join(line.strip().split()[1:])
        ts = int(time.mktime(datetime.datetime.strptime(tsstr, "%Y-%m-%d %H:%M:%S").timetuple()))
        clientlst.append((asnum,ts))
    clientlst.sort(key=lambda tup: tup[1])
    return [tup[0] for tup in clientlst]

def findAS(lst):
    cc_asn_d = json.load(open('data/cc_asn.json','r'))
    asnlst = []
    for cc in lst:
        if cc in cc_asn_d:
            asn = cc_asn_d[cc]
            asnlst.append(asn)
        else:
            #print(cc)
            continue
    return asnlst

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_path",
                        default="data/cg_path.json")
    parser.add_argument("--guard_path",
                        default="data/guard_as_bw.json")
    parser.add_argument("--topas_file",
                        default="data/top50ases.txt")
    parser.add_argument("--client_file",
                        default="")
    return parser.parse_args()

def main(args):
    # load files
    # {client: {guard: [[path1,path2],[path1,path2]]}} in which guard:[forward,reverse]
    cg_path = json.load(open(args.client_path, 'r'))
    bw_path = json.load(open(args.guard_path, 'r'))
    
    sum_weight = sum(bw_path.values())
    
    # load files
    clientlst = orderClient(args.client_file)
    clientlst = findAS(clientlst)
    print("Number of client ASes is %d" % len(clientlst))
    
    # We only consider CAIDA top 50 ASes as adversary
    topas_lst = set([line.strip() for line in open(args.topas_path,'r')])

    num_d = defaultdict(list)
    set_d = defaultdict(set) # {guard: [accumulative on-path ASes]}

    for client in clientlst: # loop through each client AS location
        for guard in cg_path[client]: # loop through each possible guard
            cur_set = set_d[guard]
            tmp_set = set(cg_path[client][guard][0] + cg_path[client][guard][1]) & topas_lst
            if cur_set:
                new_set = cur_set | tmp_set
                set_d[guard] = new_set
                num_d[guard].append(len(new_set))
            else: # first location
                set_d[guard] = tmp_set
                num_d[guard].append(len(set_d[guard]))

    # Total number of adversary ASes
    num_ases = len(topas_lst)
    
    glst = []
    for i in range(0,len(clientlst)):
        glst.append(0)
    for guard in num_d:
        for i in range(0,len(num_d[guard])):
            glst[i] += num_d[guard][i] * bw_path[guard] / (num_ases * sum_weight)

    # format:
    with open('result_files/%d_%s' % (len(clientlst), basename(args.client_file)), 'w+') as fout:
        for g in glst:
            fout.write(str(g) + '\n')


if __name__ == '__main__':
    main(parse_args())

