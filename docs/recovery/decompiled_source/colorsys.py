# Source Generated with Decompyle++
# File: colorsys.pyc (Python 3.12)

'''Conversion functions between RGB and other color systems.

This modules provides two functions for each color system ABC:

  rgb_to_abc(r, g, b) --> a, b, c
  abc_to_rgb(a, b, c) --> r, g, b

All inputs and outputs are triples of floats in the range [0.0...1.0]
(with the exception of I and Q, which covers a slightly larger range).
Inputs outside the valid range may cause exceptions or invalid outputs.

Supported color systems:
RGB: Red, Green, Blue components
YIQ: Luminance, Chrominance (used by composite video signals)
HLS: Hue, Luminance, Saturation
HSV: Hue, Saturation, Value
'''
__all__ = [
    'rgb_to_yiq',
    'yiq_to_rgb',
    'rgb_to_hls',
    'hls_to_rgb',
    'rgb_to_hsv',
    'hsv_to_rgb']
ONE_THIRD = 0.333333
ONE_SIXTH = 0.166667
TWO_THIRD = 0.666667

def rgb_to_yiq(r, g, b):
    y = 0.3 * r + 0.59 * g + 0.11 * b
    i = 0.74 * (r - y) - 0.27 * (b - y)
    q = 0.48 * (r - y) + 0.41 * (b - y)
    return (y, i, q)


def yiq_to_rgb(y, i, q):
    r = y + 0.946882 * i + 0.623557 * q
    g = y - 0.274788 * i - 0.635691 * q
    b = (y - 1.10855 * i) + 1.70901 * q
    if r < 0:
        r = 0
    if g < 0:
        g = 0
    if b < 0:
        b = 0
    if r > 1:
        r = 1
    if g > 1:
        g = 1
    if b > 1:
        b = 1
    return (r, g, b)


def rgb_to_hls(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    sumc = maxc + minc
    rangec = maxc - minc
    l = sumc / 2
    if minc == maxc:
        return (0, l, 0)
    if None <= 0.5:
        s = rangec / sumc
    else:
        s = rangec / (2 - maxc - minc)
    rc = (maxc - r) / rangec
    gc = (maxc - g) / rangec
    bc = (maxc - b) / rangec
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2 + rc - bc
    else:
        h = 4 + gc - rc
    h = h / 6 % 1
    return (h, l, s)


def hls_to_rgb(h, l, s):
    if s == 0:
        return (l, l, l)
    if None <= 0.5:
        m2 = l * (1 + s)
    else:
        m2 = l + s - l * s
    m1 = 2 * l - m2
    return (_v(m1, m2, h + ONE_THIRD), _v(m1, m2, h), _v(m1, m2, h - ONE_THIRD))


def _v(m1, m2, hue):
    hue = hue % 1
    if hue < ONE_SIXTH:
        return m1 + (m2 - m1) * hue * 6
    if None < 0.5:
        return m2
    if None < TWO_THIRD:
        return m1 + (m2 - m1) * (TWO_THIRD - hue) * 6


def rgb_to_hsv(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    rangec = maxc - minc
    v = maxc
    if minc == maxc:
        return (0, 0, v)
    s = None / maxc
    rc = (maxc - r) / rangec
    gc = (maxc - g) / rangec
    bc = (maxc - b) / rangec
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2 + rc - bc
    else:
        h = 4 + gc - rc
    h = h / 6 % 1
    return (h, s, v)


def hsv_to_rgb(h, s, v):
    if s == 0:
        return (v, v, v)
    i = None(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0:
        return (v, t, p)
    if None == 1:
        return (q, v, p)
    if None == 2:
        return (p, v, t)
    if None == 3:
        return (p, q, v)
    if None == 4:
        return (t, p, v)
    if None == 5:
        return (v, p, q)

