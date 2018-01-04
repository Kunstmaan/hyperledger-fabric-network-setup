#!/usr/bin/env python2
# Created by Guillaume Leurquin, guillaume.leurquin@accenture.com

"""parse_domain_to_subjects.py domain_name

Splits the domain name into a CN, an OU, a C and an ORG
"""


import sys

CN = sys.argv[1]
VALUES = CN.split(".")

if CN.startswith("ca."):
    CN = CN[3:]
elif CN.startswith("tlsca."):
    CN = CN[6:]

C = VALUES[-1]
if len(C) != 2:
    raise ValueError('The country code ' + C + ' can only have 2 characters')
ORG = VALUES[-2]
OU = VALUES[-3]

SUBJECTS = "/CN="+CN+"/OU="+OU+"/C="+C+"/O="+ORG

print SUBJECTS
