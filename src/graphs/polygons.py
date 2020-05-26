def is_close(poly):
    # if polygon is closed then return 1 else return 0
    if len(poly)>2 and poly[0] == poly[-1]:
        return 1
    return 0


def order_polygon(poly, segment):
    # return the same polygon but ordered starting by segment
    ordered = []
    closed = is_close(poly)
    for i, p in enumerate(poly):
        if p == segment[0]:
            j = i+1
            if i == len(poly)-1:
                j = 0
            # print(poly, j)
            if poly[j] == segment[1]:
                o1 = [poly[k] for k in range(i, len(poly)-closed)]
                o2 = [poly[k] for k in range(0, i)]
                ordered = o1 + o2
                if closed == 1:
                    ordered.append(ordered[0])
                #    print('debug case 1: {0} + {1} + {2}'.format(o1, o2, ordered[0]))
                #else:
                #    print('debug case 1: {0} + {1} + '.format(o1, o2))
                return ordered
            j = i-1
            if i == 0:
                j = len(poly)-1
            # print(poly, j)
            if poly[j] == segment[1]:
                o1 = [poly[k] for k in range(i, -1+closed, -1)]
                o2 = [poly[k] for k in range(len(poly)-1, i, -1)]
                ordered = o1 + o2
                if closed == 1:
                    ordered.append(ordered[0])
                #    print('debug case 2: {0} + {1} + {2}'.format(o1, o2, ordered[0]))
                #else:
                #    print('debug case 2: {0} + {1} + '.format(o1, o2))
                return ordered
    return None


def merge_2polygons(poly1, poly2, segment):
    # return a merged polygon from the 2 polygons that share a common segment
    print('debug p1={0} p2={1} on {2}'.format(poly1, poly2, segment))
    o1 = order_polygon(poly1, segment)
    c1 = is_close(poly1)
    o2 = order_polygon(poly2, segment)
    c2 = is_close(poly2)
    print('debug o1={0} o2={1}'.format(o1, o2))
    m1 = [o1[k] for k in range(1, len(o1)-c1)] + [o1[0]]
    m2 = [o2[k] for k in range(len(o2)-1-c2, 0, -1)]
    print('debug m1={0} + m2={1} + c={2}'.format(m1, m2, m1[0]))
    return m1 + m2 


def merge_connected_polygons(isoband):
    common = {}
    for i, polygon in enumerate(isoband):
        for point in range(0, len(polygon)-1):
            segment = (polygon[point][0], polygon[point][1], polygon[point+1][0], polygon[point+1][1])
            swapped = (segment[2], segment[3], segment[0], segment[1])
            if segment in common:
                common[segment].append(i)
            elif swapped in common:
                common[swapped].append(i)
            else:
                common[segment] = (i)

    count_common = len([1 for c in common.keys() if len(common[c])>1])
    if count_common == 0:
        return isoband

    
    new_isoband = []
    index_of_polygons = [i for i in range(0, len(isoband))]
    set_of_polygons = set(index_of_polygons)
    for segment in common.keys():
        polygons = common[segment]
        if len(polygons) == 2:
            if polygons[0] in set_of_polygons and polygons[1] in set_of_polygons:
                poly1 = isoband[polygons[0]]
                poly2 = isoband[polygons[1]]
                new_isoband.append(merge_2polygons(poly1, poly2,
                                                [(segment[0], segment[1]),
                                                 (segment[2], segment[3])]))
                # remove poly1 from set to deal with
                set_of_polygons.remove(polygons[1])
                # update common and replace poly1 by poly2
                for k in common.keys():
                    v = common[k]
                    new_v = [i if v[i] != polygons[1] else polygons[0] for i in v]
                    common[k] = new_v

    for p in set_of_polygons:
        new_isoband.append(isoband[p])
    
    # need to iterate
    return merge_connected_polygons(new_isoband)
