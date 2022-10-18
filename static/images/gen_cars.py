#!/usr/bin/env python3

colors = [0xff0000, 0x00ffff, 0x8000ff, 0x80ff00, 0xff0098, 0x00ff3e, 0xffce00, 0x0042ff]

with open('car_base.svg') as base:
    btxt = base.read()
    for i, c in enumerate(colors):
        with open(f'car_{i}.svg', 'w+') as output:
            old = '#00ff00'
            new = '#%06x' % c
            output.write(btxt.replace(old, new))
