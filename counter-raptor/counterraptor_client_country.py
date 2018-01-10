#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##################################################
# counterraptor_client_country.py
# compute resilience probability
# Input:
# List of Tor client ASes (--client_file, default="./all_ases.txt")
# Tor guard relay bandwidth (--guard_file, default="../data/guard_as_bw.json")
# Tor client to guard resiliences (--resil_file, default="../data/cg_resilience.json")
# Output:
# Resilience probabilities for each client AS of each alpha value (al[alpha]_cl[clientAS].txt)
##################################################


import sys
import json
import math
import argparse
import datetime
import time
from os.path import basename
from copy import deepcopy


def helper_calc(lst,k):
    s = sum(lst)
    for i in range(0,len(lst)):
        lst[i] = (lst[i]*k)/s
    return lst

def recalcprob(lst,k):
    tmplst = helper_calc(lst,k)
    finallst = [0] * len(tmplst)
    counter = 0
    while max(tmplst) > 1:
        for i in range(0,len(tmplst)):
            if tmplst[i] > 1:
                finallst[i] = 1
                tmplst[i] = 0
                counter += 1
        if max(tmplst) > 0:
            tmplst = helper_calc(tmplst,k-counter)
        else:
            break
    for i in range(0,len(tmplst)):
        if tmplst[i] != 0:
            finallst[i] = tmplst[i]
    return [i/k for i in finallst]

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
    cc_asn_d = json.load(open('cc_asn.json','r'))
    asnlst = []
    for cc in lst:
        if cc in cc_asn_d:
            asn = cc_asn_d[cc]
            asnlst.append(asn)
        else:
            print(cc)
    return asnlst

def calc_mobile(alpha, clientlst, args, num_hijack):
    guard_as_bw = json.load(open(args.guard_file,'r'))
    asn_lst = []
    bw_lst = []
    
    for asn in guard_as_bw:
        asn_lst.append(asn)
        bw_lst.append(guard_as_bw[asn])

    #normalize bandwidth
    s = sum([int(i) for i in bw_lst])
    bw_lst = [float(i)/s for i in bw_lst]

    client_dict = json.load(open(args.resil_file,'r'))
    # sanity check to make sure all clients have values
    for clientas in clientlst:
        if clientas not in client_dict:
            print("%s file failed on AS %s" % (args.client_file, clientas))
            sys.exit(0)

    # hijack_dict: {client: {guard: [as1,as2,...]}}
    hijack_dict = json.load(open(args.hijack_file,'r'))

    sample_size = max(int(math.floor(len(guard_as_bw)*args.sample_size)),1)

    firstclient = clientlst[0]
    remain_client = clientlst[1:]

    lst_w = []
    curdict = client_dict[firstclient]
    if sum(curdict.values()) == 0:
        print("%s first client have all 0 values" % firstclient)
        sys.exit(0)
    d_keys = list(curdict.keys())
    d_vals = recalcprob(list(curdict.values()),sample_size)
    lst_w = []
    for i in range(0,len(asn_lst)):
        a = asn_lst[i]
        r = d_vals[d_keys.index(a)] # new value
        b = bw_lst[i]
        weight = alpha * r + (1 - alpha) * float(b)
        lst_w.append(weight)
    total_w = sum(lst_w)
    norm_w = [i/total_w for i in lst_w] # weight represents prob. of each guard being chosen

    glst = []
    # prob of being hijacked for first client
    plst = []
    hijackd = deepcopy(hijack_dict[firstclient])
    for gd in hijackd:
        hijackd[gd] = set(hijackd[gd])
    for i in range(0,len(norm_w)):
        a = asn_lst[i]
        pr = norm_w[i] * float(len(hijackd[a]) / num_hijack) # prob. of being hijacked
        plst.append(pr)
    gval = sum(plst)
    glst.append(gval)

    #remain client
    for rc in remain_client:
        plst = []
        # are the following lines necessary?
        curdict = client_dict[rc]
        if sum(curdict.values()) == 0:
            print("%s client have all 0 values" % rc)
            sys.exit(0)
        # get the current attacking AS and add to the list
        cur_hd = hijack_dict[rc]
        for gd in hijackd: # loop through each guard
            hijackd[gd] = hijackd[gd] | set(cur_hd[gd])
        for i in range(0,len(norm_w)):
            pr_guard = norm_w[i]
            a = asn_lst[i]
            pr = norm_w[i] * float(len(hijackd[a]) / num_hijack) # prob. of being hijacked
            plst.append(pr)
        gval = sum(plst)
        glst.append(gval)
    return glst

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard_file",
                        default="../data/guard_as_bw.json")
    parser.add_argument("--resil_file",
                        default="../data/top_mob/cg_resilience.json")
    parser.add_argument("--hijack_file",
                        default="../data/top_mob/cg_hijack_as.json")
    parser.add_argument("--client_file",
                        default="./all_ases.txt")
    parser.add_argument("--sample_size", type=float, default=0.1)
    return parser.parse_args()

def main(args):
    clientlst = orderClient(args.client_file)
    clientlst = findAS(clientlst)
    print("Number of ASes is %d" % len(clientlst))
    
    num_hijack = 50 # hardcoded number of hijacking ASes
    new_resil = calc_mobile(0.5, clientlst, args, num_hijack)

    with open('dat_files/%d_%s' % (len(clientlst), basename(args.client_file)), 'w+') as fout:
        for g in new_resil: #ratio_resil:
            fout.write(str(g) + '\n')


if __name__ == '__main__':
    main(parse_args())

