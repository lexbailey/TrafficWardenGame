#!/usr/bin/env python3
from traffic_logic import TrafficWardenLogic, Dir
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.color import Color, parse_rgb_hex
from rich.style import Style


game = TrafficWardenLogic(8)


console = Console()

def arrow(dir_):
    match dir_:
        case 'left':
            return '\U0001f880'
        case 'right':
            return '\U0001f882'
        case 'up':
            return '\U0001f881'
        case 'down':
            return '\U0001f883'
    return ''

def arrow_parts(dir_):
    char = arrow(dir_)
    match dir_:
        case 'left':
            return (char, ' \n', '   \n', '   ')
        case 'right':
            return (' ', f'{char}\n', '   \n', '   ')
        case 'up':
            return (' ', ' \n', f' {char} \n', '   ')
        case 'down':
            return (' ', ' \n', '   \n', f' {char} ')
        case '':
            return (' ', ' \n', '   \n', '  ')
    assert False

def render_cell(p):
    tile, color = p
    arrow(tile)
    l, r, u, d = arrow_parts(tile)
    block = (' ', '')
    if color != '':
        block = ('\u2588', Style(color=Color.from_triplet(parse_rgb_hex(color))))
    return Text.assemble(
        (u, ''),
        (l, ''),
        block,
        (r, ''),
        (d, ''),
    )

def render(console, data):
    table = Table(show_lines=True)
    table.add_column('')
    for i in range(10):
        table.add_column(str(i))
    
    for i in reversed(range(10)):
        table.add_row(str(i), *[
            render_cell(p) for p in [data['grid'][j][i] for j in range(10)]
        ])
    
    console.print(table)

game.put_tile((1,3), Dir.down)
game.put_tile((4,3), Dir.left)
game.put_tile((2,6), Dir.up)
game.put_tile((6,9), Dir.right)


render_data = game.get_projector_render_data()
render(console, render_data)

import time
for i in range(20):
    time.sleep(0.7)
    game.step([0,1,2,3,4,5,6,7])
    render_data = game.get_projector_render_data()
    render(console, render_data)