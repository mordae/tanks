#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

# Potrebujeme pro vypocty uhlu.
import math

# Potrebujeme pro nahodne uhybne manevry. :-O
import random

# Potrebujeme pro kresleni, spravu oken a tak.
import pyglet
from pyglet import gl
from pyglet.window import key

# Pro kopirovani slozitejsich dat.
from copy import deepcopy


## Herni konstanty
# Velikost okna (v pixelech)
SIRKA = 900
VYSKA = 600

# Rozmery tanku
TANK_DELKA = 40
TANK_SIRKA = 30
TANK_OBLAST_KOLIZE = 40
TANK_OBLAST_ZASAHU = 30

# Rozmery hlavne
HLAVEN_DELKA = 30
HLAVEN_SIRKA = 10
HLAVEN_POSUN = 15

# Velikost granatu
GRANAT_DELKA = 8
GRANAT_SIRKA = 4

# Rychlost tanku
RYCHLOST_JIZDY = 200
RYCHLOST_ROTACE = 180
RYCHLOST_GRANATU = 400

# Rychlost strelby
DOBA_NABIJENI = 1.0

# Velikost pisma a pozice skore
PISMO_VELIKOST = 42
SKORE_ODSAZENI = 30

# Barvy tanku a granatu
BARVY_TANKU = [(1.0, 0.1, 0.1), (0.1, 0.1, 1.0)]
BARVA_HLAVNE = (1.0, 1.0, 0.1)
BARVA_GRANATU = (1.0, 0.1, 0.1)

# Kolik maji tanky na zacatku zivotu
POCET_ZIVOTU = 3
ZIVOT_ODSAZENI = SKORE_ODSAZENI + PISMO_VELIKOST + 30
ZIVOT_VELIKOST = 10

# Startovni polohy
# Na zacatku mame dva tanky mirici na sebe pres celou obrazovku
TANKY_START = [
    [50, VYSKA // 2, 270],
    [SIRKA - 50, VYSKA // 2, 90],
]

# Zadne granaty v single-playeru.
GRANATY_START = [
]

# Oba tanky na zacatku nabijeji.
NABIJENI_START = [DOBA_NABIJENI, DOBA_NABIJENI]

## Stav hry
skore = [0, 0]
zivoty = [POCET_ZIVOTU, POCET_ZIVOTU]
ruda_pamet = {}

tanky = TANKY_START
granaty = GRANATY_START
nabijeni = NABIJENI_START

klavesy = set()


def reset():
    """
    Reset hry do pocatecniho stavu.
    Skore zustava.
    """

    global tanky, granaty, nabijeni, zivoty, ruda_pamet

    tanky = deepcopy(TANKY_START)
    granaty = deepcopy(GRANATY_START)
    nabijeni = deepcopy(NABIJENI_START)

    zivoty = [POCET_ZIVOTU, POCET_ZIVOTU]
    ruda_pamet = {}

    tanky[0][1] += random.randrange(-100, +100)
    tanky[1][1] += random.randrange(-100, +100)


def se_srazi(x1, y1, x2, y2, polomer):
    return abs(x1 - x2) < polomer and abs(y1 - y2) < polomer


def prepocitej(dt):
    """
    Spocitej novy stav hry po uplynuti trochy casu (dt).
    """

    mysli_rudy(0, 1, ruda_pamet)

    global granaty

    jizda = [
        (1.0 if ('vpred', 0) in klavesy else 0) -
        (1.0 if ('zpet',  0) in klavesy else 0),

        (1.0 if ('vpred', 1) in klavesy else 0) -
        (1.0 if ('zpet',  1) in klavesy else 0),
    ]

    rotace = [
        (-1 if ('vpravo', 0) in klavesy else 0) +
        (+1 if ('vlevo',  0) in klavesy else 0),

        (-1 if ('vpravo', 1) in klavesy else 0) +
        (+1 if ('vlevo',  1) in klavesy else 0),
    ]

    strelba = [
        ('spoust', 0) in klavesy,
        ('spoust', 1) in klavesy,
    ]

    hits = []

    # Posun granaty ve smeru letu.
    for i, (_, _, r) in enumerate(granaty):
        uhel = math.radians(r + 90)
        granaty[i][0] += dt * RYCHLOST_GRANATU * math.cos(uhel)
        granaty[i][1] += dt * RYCHLOST_GRANATU * math.sin(uhel)

        gx = granaty[i][0]
        gy = granaty[i][1]

        # Pohlidej pripadne zasahy tanku. ;-)
        for j, (tx, ty, _) in enumerate(tanky):
            if se_srazi(gx, gy, tx, ty, TANK_OBLAST_ZASAHU):
                zivoty[j] -= 1
                hits.append([gx, gy, r])
                if zivoty[j] <= 0:
                    skore[int(not j)] += 1
                    return reset()

    for hit in hits:
        if hit in granaty:
            granaty.remove(hit)

    # Uchovej pouze granaty, ktere nevyletely z mapy.
    granaty = [g for g in granaty if 0 < g[0] < SIRKA and 0 < g[1] < VYSKA]

    # Uprav rotaci tanku.
    for i, r in enumerate(rotace):
        tanky[i][2] += dt * r * RYCHLOST_ROTACE

    # Posun tanky smerem pohybu.
    for i, (x, y, r) in enumerate(tanky):
        uhel = math.radians(r + 90)
        tanky[i][0] += dt * jizda[i] * RYCHLOST_JIZDY * math.cos(uhel)
        tanky[i][1] += dt * jizda[i] * RYCHLOST_JIZDY * math.sin(uhel)

        # Nedovol tankum vyjet z mapy.
        tanky[i][0] = max(tanky[i][0], TANK_OBLAST_KOLIZE)
        tanky[i][0] = min(tanky[i][0], SIRKA - TANK_OBLAST_KOLIZE)
        tanky[i][1] = max(tanky[i][1], TANK_OBLAST_KOLIZE)
        tanky[i][1] = min(tanky[i][1], VYSKA - TANK_OBLAST_KOLIZE)

        # Pohlidej pripadne srazky a nenech tanky jezdit pres sebe.
        for j, (jx, jy, _) in enumerate(tanky):
            if i != j:
                if se_srazi(tanky[i][0], y, jx, jy, TANK_OBLAST_KOLIZE):
                    tanky[i][0] = x
                elif se_srazi(x, tanky[i][1], jx, jy, TANK_OBLAST_KOLIZE):
                    tanky[i][1] = y
                elif se_srazi(tanky[i][0], tanky[i][1], jx, jy, TANK_OBLAST_KOLIZE):
                    tanky[i][0] = x
                    tanky[i][1] = y

    # Nabijej hlavne.
    for i, n in enumerate(nabijeni):
        nabijeni[i] = max(0, n - dt)

    # Strilej, pokud to hrac chce.
    for i, (x, y, r) in enumerate(tanky):
        if strelba[i] and not nabijeni[i]:
            uhel = math.radians(r + 90)

            granaty.append([
                x + TANK_OBLAST_KOLIZE * math.cos(uhel),
                y + TANK_OBLAST_KOLIZE * math.sin(uhel),
                r,
            ])

            nabijeni[i] = DOBA_NABIJENI


def nakresli_text(text, x, y, zarovnani='left', barva=(1, 1, 1)):
    """Nakresli dany text na danou pozici s danym zarovnanim a barvou."""

    pyglet.text.Label(
        text,
        x=x, y=y,
        anchor_x=zarovnani,
        color=(
            int(barva[0] * 255),
            int(barva[1] * 255),
            int(barva[2] * 255),
            255,
        ),
        font_size=PISMO_VELIKOST,
        font_name='League Gothic',
    ).draw()


def nakresli_tank(x, y, rotace, barva):
    """Nakresli tank na dane pozici, s rotaci a v dane barve."""

    # Zacentruj kresleni na stred tela tanku.
    gl.glTranslatef(x, y, 0.0)

    # Aplikuj aktualni rotaci.
    gl.glRotatef(rotace, 0.0, 0.0, 1.0)

    # Nakresli telo tanku ve zvolene barve.
    gl.glColor3f(*barva)
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(-TANK_SIRKA / 2, -TANK_DELKA / 2)
    gl.glVertex2f(-TANK_SIRKA / 2, +TANK_DELKA / 2)
    gl.glVertex2f(+TANK_SIRKA / 2, +TANK_DELKA / 2)
    gl.glVertex2f(+TANK_SIRKA / 2, -TANK_DELKA / 2)
    gl.glEnd()

    # Nakresli hlaven tanku ve standardni barve.
    gl.glColor3f(*BARVA_HLAVNE)
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(-HLAVEN_SIRKA / 2, -HLAVEN_DELKA / 2 + HLAVEN_POSUN)
    gl.glVertex2f(-HLAVEN_SIRKA / 2, +HLAVEN_DELKA / 2 + HLAVEN_POSUN)
    gl.glVertex2f(+HLAVEN_SIRKA / 2, +HLAVEN_DELKA / 2 + HLAVEN_POSUN)
    gl.glVertex2f(+HLAVEN_SIRKA / 2, -HLAVEN_DELKA / 2 + HLAVEN_POSUN)
    gl.glEnd()

    # Vrat rotaci a centrovani do puvodniho stavu.
    gl.glRotatef(-rotace, 0.0, 0.0, 1.0)
    gl.glTranslatef(-x, -y, 0.0)


def nakresli_granat(x, y, rotace, barva):
    """Nakresli granat na dane pozici a v dane barve."""

    gl.glTranslatef(x, y, 0.0)
    gl.glRotatef(rotace, 0.0, 0.0, 1.0)
    gl.glColor3f(*barva)
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(-GRANAT_SIRKA / 2, -GRANAT_DELKA / 2)
    gl.glVertex2f(-GRANAT_SIRKA / 2, +GRANAT_DELKA / 2)
    gl.glVertex2f(+GRANAT_SIRKA / 2, +GRANAT_DELKA / 2)
    gl.glVertex2f(+GRANAT_SIRKA / 2, -GRANAT_DELKA / 2)
    gl.glEnd()
    gl.glRotatef(-rotace, 0.0, 0.0, 1.0)
    gl.glTranslatef(-x, -y, 0.0)


def nakresli_zivot(x, y, barva):
    """Nakresli zivot na dane pozici a v dane barve."""

    gl.glTranslatef(x, y, 0.0)
    gl.glRotatef(45, 0.0, 0.0, 1.0)
    gl.glColor3f(*barva)
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(-ZIVOT_VELIKOST / 2, -ZIVOT_VELIKOST / 2)
    gl.glVertex2f(-ZIVOT_VELIKOST / 2, +ZIVOT_VELIKOST / 2)
    gl.glVertex2f(+ZIVOT_VELIKOST / 2, +ZIVOT_VELIKOST / 2)
    gl.glVertex2f(+ZIVOT_VELIKOST / 2, -ZIVOT_VELIKOST / 2)
    gl.glEnd()
    gl.glRotatef(-45, 0.0, 0.0, 1.0)
    gl.glTranslatef(-x, -y, 0.0)


def vykresli():
    """Vykresli stav hry."""

    # Prebarvi cele okno na cerno.
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    # Nakresli tanky.
    for i, tank in enumerate(tanky):
        nakresli_tank(*tank, BARVY_TANKU[i])

    # Nakresli granaty.
    for granat in granaty:
        nakresli_granat(*granat, BARVA_GRANATU)

    # Skore prvniho hrace.
    nakresli_text(str(skore[0]),
                  x=SKORE_ODSAZENI,
                  y=VYSKA - SKORE_ODSAZENI - PISMO_VELIKOST,
                  zarovnani='left',
                  barva=BARVY_TANKU[0])

    for i in range(zivoty[0]):
        nakresli_zivot(SKORE_ODSAZENI + i * ZIVOT_VELIKOST * 2, VYSKA - ZIVOT_ODSAZENI, BARVY_TANKU[0])

    nakresli_text(str(skore[1]),
                  x=SIRKA - SKORE_ODSAZENI,
                  y=VYSKA - SKORE_ODSAZENI - PISMO_VELIKOST,
                  zarovnani='right',
                  barva=BARVY_TANKU[1])

    for i in range(zivoty[1]):
        nakresli_zivot(SIRKA - SKORE_ODSAZENI - i * ZIVOT_VELIKOST * 2, VYSKA - ZIVOT_ODSAZENI, BARVY_TANKU[1])


def stisk(symbol, modifikatory):
    """Uzivatel tiskne hlavesu."""

    if symbol == key.UP:
        klavesy.add(('vpred', 1))
    elif symbol == key.DOWN:
        klavesy.add(('zpet', 1))
    elif symbol == key.LEFT:
        klavesy.add(('vlevo', 1))
    elif symbol == key.RIGHT:
        klavesy.add(('vpravo', 1))
    elif symbol == key.SPACE:
        klavesy.add(('spoust', 1))


def pusteni(symbol, modifikatory):
    """Uzivatel pustil klavesu."""

    if symbol == key.UP:
        klavesy.discard(('vpred', 1))
    elif symbol == key.DOWN:
        klavesy.discard(('zpet', 1))
    elif symbol == key.LEFT:
        klavesy.discard(('vlevo', 1))
    elif symbol == key.RIGHT:
        klavesy.discard(('vpravo', 1))
    elif symbol == key.SPACE:
        klavesy.discard(('spoust', 1))


def mysli_rudy(i, t, pamet):
    nase_x, nase_y, nase_rotace = tanky[i]
    jeho_x, jeho_y, jeho_rotace = tanky[t]

    pamet.setdefault('blizko', False)
    pamet.setdefault("bacha", False)

    # Koukej se po protivníkovi a snaž se to sypat jeho směrem.
    smer = math.atan2(jeho_x - nase_x, jeho_y - nase_y)
    smer = (math.degrees(smer) + nase_rotace) % 360

    # Budeme davat bacha na granaty...
    bacha = False
    for gx, gy, gr in granaty:
        gs = math.atan2(nase_x - gx, nase_y - gy)
        gs = (math.degrees(gs) + gr) % 360

        if pamet["bacha"] and gs < 60 or gs > 300:
            bacha = True
            break
        elif gs < 10 or gs > 350:
            bacha = True
            break

    pamet["bacha"] = bacha

    vzdalenost = ((jeho_x - nase_x) ** 2 + (jeho_y - nase_y) ** 2) ** (1/2)

    if pamet["blizko"] and vzdalenost < 400:
        blizko = True
    elif vzdalenost < 200:
        blizko = True
    else:
        blizko = False

    pamet["blizko"] = blizko

    if bacha:
        if ('vpred', i) not in klavesy and ('zpet', i) not in klavesy:
            klavesy.add(('vpred', i))

        if gs < 10 or gs > 350:
            if ('vpravo', i) in klavesy:
                klavesy.discard(('vlevo', i))
            elif ('vlevo', i) in klavesy:
                klavesy.discard(('vpravo', i))
            else:
                klavesy.add((random.choice(['vlevo', 'vpravo']), i))

    else:
        if blizko:
            klavesy.add(('zpet', i))
            klavesy.discard(('vpred', i))
        else:
            klavesy.add(('vpred', i))
            klavesy.discard(('zpet', i))

        if smer < 5 or smer > 355:
            klavesy.discard(('vpravo', i))
            klavesy.discard(('vlevo', i))
        elif smer > 180:
            klavesy.discard(('vpravo', i))
            klavesy.add(('vlevo', i))
        else:
            klavesy.discard(('vlevo', i))
            klavesy.add(('vpravo', i))

    if smer < 5 or smer > 355:
        klavesy.add(('spoust', i))
    else:
        klavesy.discard(('spoust', i))


# Nastavime prvotni stav.
reset()

# Pripravime konfiguraci s vyhlazovanim (4x multisampling).
config = pyglet.gl.Config(sample_buffers=1, samples=4)

# Vytvorime okno, do ktereho budeme kreslit.
window = pyglet.window.Window(width=SIRKA, height=VYSKA, config=config)

# Oknu priradime funkce, ktere budou reagovat na udalosti.
window.push_handlers(
    on_draw=vykresli,
    on_key_press=stisk,
    on_key_release=pusteni,
)

# Nastavime casovac na 60 fps.
pyglet.clock.schedule(prepocitej)

# A spustime hru.
pyglet.app.run()

# vim:set sw=4 ts=4 et:
