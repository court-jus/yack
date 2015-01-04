# -*- coding: utf-8 -*-

from wand.image import Image
import pdb
import os

WORK_RESOLUTION = 100
BASEDIR = '/tmp'
# MM = INCH / 25.4

def unit_convert(unit=1.0, base_resolution=300, work_resolution=300):

    def px(val):
        if work_resolution != base_resolution:
            return int(val * unit * float(work_resolution) / float(base_resolution))
        return int(val * unit)

    return px

px = unit_convert(work_resolution=WORK_RESOLUTION)
    
CARDW = px(736)
CARDH = px(1030)
MTOP = px(95)
MLEFT = px(161)
TILEW = 3
TILEH = 3
INNW = px(10)
INNH = px(10)

with Image(filename='/tmp/micro.pdf', resolution=WORK_RESOLUTION) as img:
    npages = len(img.sequence)
    ncards = TILEW * TILEH
    for pnum in [1]:
        page = img.sequence[pnum]
        for cnum in range(ncards):
            rownum = cnum / TILEW
            colnum = cnum % TILEH
            print pnum, rownum, colnum
            filename = os.path.join(BASEDIR, 'page%d-card%d.png' % (pnum, cnum))
            left = MLEFT + colnum * (CARDW + INNW)
            right = left + CARDW
            top = MTOP + rownum * (CARDH + INNH)
            bottom = top + CARDH
            with page[left:right, top:bottom] as card:
                card.save(filename=filename)
