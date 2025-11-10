import random

def board(__from__, __to__, status):
    if status == 'start':
        pos = init_pos()
        status == 'ongoing'
    if status == 'ongoing':
        return

pieces = dict(w_general=1, b_general=1,
     w_advisor=2, b_advisor=2,
     w_elephant=2, b_elephant=2,
     w_chariot=2, b_chariot=2,
     w_horse=2, b_horse=2,
     w_pawn=5, b_pawn=5,
     w_catapult=2, b_catapult=2)

pool = [piece for piece, count in pieces.items() for _ in range(count)]
random.shuffle(pool)

def init_pos() -> dict:
    pos = dict(a1='unknown',a2='unknown',a3='unknown',a4='unknown',
           b1='unknown',b2='unknown',b3='unknown',b4='unknown',
           c1='unknown',c2='unknown',c3='unknown',c4='unknown',
           d1='unknown',d2='unknown',d3='unknown',d4='unknown',
           e1='unknown',e2='unknown',e3='unknown',e4='unknown',
           f1='unknown',f2='unknown',f3='unknown',f4='unknown',
           g1='unknown',g2='unknown',g3='unknown',g4='unknown',
           h1='unknown',h2='unknown',h3='unknown',h4='unknown',)
    return pos
    print("test")
    pos = []
    for i in range(1,9):
        for y in range(1,5):
            x = files[int(i)]
            pos.append(f"{x}{y}")
    return pos
def get_pos():

    a1 = init_pos()
    print(f"POS: {a1}")

get_pos()
