#!/usr/bin/env python3

colors = [0xff0000, 0x00ffff, 0x8000ff, 0x80ff00, 0xff0098, 0x00ff3e, 0xffce00, 0x0042ff]

for (base, outname) in [
        ('car_base.svg', 'car_{}.svg'),
        ('goal_tile_base.svg', 'goal_tile_{}.svg'),
        ('arrow_tile_base.svg', 'arrow_tile_{}.svg'),
    ]:
    with open(base) as base:
        btxt = base.read()
        for i, c in enumerate(colors):
            with open(outname.format(i), 'w+') as output:
                old = '#00ff00'
                new = '#%06x' % c
                output.write(btxt.replace(old, new))
