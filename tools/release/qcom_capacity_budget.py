#!/usr/bin/env python3
"""Scenario arithmetic for future QCOM work; unknown peaks always prevent GO."""
from __future__ import annotations
import argparse
import json
GIB=1024**3
SOURCE_BYTES=1009*1024**2  # measured host checkout, including pinned submodules/assets
ARCHIVE_BYTES=223006720
EXTRACTED_BYTES=219518275
RESERVE_BYTES=2*GIB
SCENARIOS=(
    ('minimal_staged_source',0,0,0,0),
    ('source_plus_toolchain',1*GIB,0,0,0),
    ('first_warp_pilot',1*GIB,512*1024**2,1*GIB,0),
    ('large_onnx_compilation',1*GIB,2*GIB,4*GIB,0),
    ('sequential_six_outputs',1*GIB,2*GIB,4*GIB,2*GIB),
    ('complete_native_product',1*GIB,3*GIB,4*GIB,2*GIB),
)

def calculate(free_bytes:int, *, include_archive_copy:bool=False)->dict:
    if not isinstance(free_bytes,int) or isinstance(free_bytes,bool) or free_bytes<0:
        raise ValueError('invalid free-space observation')
    rows=[]
    for name,toolchain,cache,scratch,outputs in SCENARIOS:
        fixed=SOURCE_BYTES+RESERVE_BYTES+(ARCHIVE_BYTES+EXTRACTED_BYTES if include_archive_copy else 0)
        subtotal=fixed+toolchain+cache+scratch+outputs
        rows.append({'name':name,'fixed_measured_source_bytes':SOURCE_BYTES,
            'reserve_bytes':RESERVE_BYTES,'archive_and_extracted_copy_bytes':ARCHIVE_BYTES+EXTRACTED_BYTES if include_archive_copy else 0,
            'toolchain_estimate_bytes':toolchain,'cache_estimate_bytes':cache,
            'scratch_estimate_bytes':scratch,'outputs_estimate_bytes':outputs,
            'scenario_total_bytes':subtotal,'arithmetic_headroom_bytes':free_bytes-subtotal,
            'scenario_scratch_peak_measured':False,
            'decision':'NO_GO_UNKNOWN_PEAK' if free_bytes>=subtotal else 'NO_GO_ESTIMATE_EXCEEDS_FREE'})
    return {'schema_version':1,'observed_free_bytes':free_bytes,'observation_is_snapshot':True,
        'measured_source_checkout_bytes_approximate':SOURCE_BYTES,
        'archive_and_extracted_bytes_measured':ARCHIVE_BYTES+EXTRACTED_BYTES,
        'classification':'REQUIRED_CAPACITY_UNKNOWN','device_qualification':'NOT_TESTED','scenarios':rows}

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observed-free-bytes',type=int,required=True)
    parser.add_argument('--include-archive-copy',action='store_true')
    args=parser.parse_args()
    print(json.dumps(calculate(args.observed_free_bytes,include_archive_copy=args.include_archive_copy),indent=2,sort_keys=True))
if __name__=='__main__':main()
