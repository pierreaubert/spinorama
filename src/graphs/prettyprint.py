pstart = 0
pref = {}

def pp(poly):
    global pstart
    global pref
    for point in poly:
        if point[0] not in pref:
            pref[point[0]] = {}
        if point[1] not in pref[point[0]]:
            pref[point[0]][point[1]] = 'p{0}'.format(pstart)
            pstart += 1
    #for k1, v1 in pref.items():
    #    for k2, v2 in v1.items():
    #        print('{0} = [{1}, {2}]'.format(v2, k1, k2))
    p ='['
    for point in poly:
        p += pref[point[0]][point[1]]
        p += ','
    p += ']'
    return p

def pps(isoband):
    p = '['
    for poly in isoband:
        p += pp(poly)
    p += ']'
        
    return p

