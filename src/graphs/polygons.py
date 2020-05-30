import logging
from .prettyprint import pp

def is_close(poly):
    # if polygon is closed then return 1 else return 0
    if len(poly)>2 and poly[0] == poly[-1]:
        return 1
    return 0

def is_equal(p1, p2):
    if p1[0] == p2[0] and p1[1] == p2[1]:
        return True
    return False


def order_polygon(poly, segment):
    # return the same polygon but ordered starting by segment
    ordered = []
    closed = is_close(poly)
    for i, p in enumerate(poly):
        # print('debug i={0} p={1} segment={2}'.format(i, p, segment))
        if is_equal(p, segment[0]):
            j = i+1
            if i == len(poly)-1:
                j = 0
            # print('debug order poly{0} j={1}'.format(poly, j))
            if is_equal(poly[j], segment[1]):
                o1 = [poly[k] for k in range(i, len(poly)-closed)]
                o2 = [poly[k] for k in range(0, i)]
                ordered = o1 + o2
                if closed == 1:
                    ordered.append(ordered[0])
                #    print('debug order case 1: {0} + {1} + {2}'.format(o1, o2, ordered[0]))
                #else:
                #    print('debug order case 1: {0} + {1} + '.format(o1, o2))
                return ordered
            j = i-1
            if i == 0:
                j = len(poly)-1
            #print('debug order poly{0} j={1}'.format(poly, j))
            if is_equal(poly[j], segment[1]):
                o1 = [poly[k] for k in range(i, -1+closed, -1)]
                o2 = [poly[k] for k in range(len(poly)-1, i, -1)]
                ordered = o1 + o2
                if closed == 1:
                    ordered.append(ordered[0])
                #    print('debug order case 2: {0} + {1} + {2}'.format(o1, o2, ordered[0]))
                #else:
                #    print('debug order case 2: {0} + {1} + '.format(o1, o2))
                return ordered
    return None


def merge_2polygons(poly1, poly2, segment):
    # return a merged polygon from the 2 polygons that share a common segment
    # print('debug merge p1={0} p2={1} on {2}'.format(poly1, poly2, segment))
    o1 = order_polygon(poly1, segment)
    c1 = is_close(poly1)
    o2 = order_polygon(poly2, segment)
    c2 = is_close(poly2)
    # print('debug merge o1={0} o2={1}'.format(o1, o2))
    m1 = [o1[k] for k in range(1, len(o1)-c1)] + [o1[0]]
    m2 = [o2[k] for k in range(len(o2)-1-c2, 0, -1)]
    # print('debug merge m1={0} + m2={1} + c={2}'.format(m1, m2, m1[0]))
    return m1 + m2


def merge_connected_polygons(isoband):

    # which polygons share a segment?
    segment_to_polygons = {}
    for i, polygon in enumerate(isoband):
        for point in range(0, len(polygon)-1):
            segment = (polygon[point][0], polygon[point][1], polygon[point+1][0], polygon[point+1][1])
            swapped = (segment[2], segment[3], segment[0], segment[1])
            if segment in segment_to_polygons:
                segment_to_polygons[segment].append(i)
            elif swapped in segment_to_polygons:
                segment_to_polygons[swapped].append(i)
            else:
                segment_to_polygons[segment] = [i]

    # print('debug: segment_to_polygons segment:')
    #for i in segment_to_polygons.keys():
    #    print('    {0}: {1}'.format(i, segment_to_polygons[i]))

    # reverse of above
    polygons_to_segment = {}
    for segment, polys in segment_to_polygons.items():
        if len(polys) == 2:
            p1 = polys[0]
            p2 = polys[1]
            polygons_to_segment[(p1, p2)] = [(segment[0], segment[1]),
                                             (segment[2], segment[3])]

    #print('debug: polygons_to_segment:')
    #for polys, segment in polygons_to_segment.items():
    #    print('    {0}: {1}'.format(polys, segment))

    pointer_polygons = {}
    count_connected = 0
    connected_polygons = {}
    #print('debug: connected_polygons:')
    for c in segment_to_polygons.keys():
        len_c = len(segment_to_polygons[c])
        if len_c == 2:
            # polygons are connected
            p1 = segment_to_polygons[c][0]
            p2 = segment_to_polygons[c][1]
            #print('debug c={0} p1={1} p2={2}'.format(c, p1, p2))
            if p1 in pointer_polygons:
                #print('debug case1 add {1} to pp[{0}]'.format(p1, p2))
                connected_polygons[pointer_polygons[p1]].add(p2)
                pointer_polygons[p2] = pointer_polygons[p1]
            elif p2 in pointer_polygons:
                #print('debug case2 add {0} to pp[{1}]'.format(p1, p2))
                connected_polygons[pointer_polygons[p2]].add(p1)
                pointer_polygons[p1] = pointer_polygons[p2]
            else:
                connected_polygons[count_connected] = set([p1, p2])
                pointer_polygons[p1] = count_connected
                pointer_polygons[p2] = count_connected
                #print('debug case3 pp[{0}]={2} pp[{1}]={2}'.format(p1, p2, count_connected))
                count_connected += 1
        elif len_c > 2:
            logging.error('More than 2 polygons connected to one segment')

    #print('debug count connected {0}'.format(count_connected))
    #print('debug pointer_polygons {0}'.format(pointer_polygons))
    #print('debug connected_polygons')
    #for cp_k, cp_v in connected_polygons.items():
    #    print('  {0} {1}'.format(cp_k, cp_v))

    if count_connected == 0:
        return isoband

    new_isoband = []
    for i, polyset in connected_polygons.items():
        try:
            poly0 = polyset.pop()
            merged_polygon = isoband[poly0]
            while 1:
                #print('debug polyset={0} poly0={1} merged_polygon={2}'.format(i, poly0, pp(merged_polygon)))
                match = []
                for p, s in polygons_to_segment.items():
                    #print('  p={0} s={1}'.format(p, s))
                    if p[0] == poly0:
                        merged_polygon = merge_2polygons(merged_polygon, isoband[p[1]], s)
                        #print('    merge {0} and {1}+{2} = {3}'.format(poly0, p[1], pp(isoband[p[1]]), pp(merged_polygon)))
                        match.append(p)
                    elif p[1] == poly0:
                        merged_polygon = merge_2polygons(merged_polygon, isoband[p[0]], s)
                        #print('    merge {0} and {1}+{2} = {3}'.format(poly0, p[0], pp(isoband[p[0]]), pp(merged_polygon)))
                        match.append(p)
                for p in match:
                    del polygons_to_segment[p]
                poly0 = polyset.pop()
        except KeyError as ke2:
            #print('debug get a KeyError {0}, appending {1}'.format(ke2, pp(merged_polygon)))
            new_isoband.append(merged_polygon)
       

    # add single polygons
    for i, polygon in enumerate(isoband):
        if i not in pointer_polygons:
            #print('debug adding polygon[{0}] = {1}'.format(i, polygon))
            new_isoband.append([p for p in polygon])

    #for i, polygon in enumerate(isoband):
    #    print('debug:  INPUT {0} {1}'.format(i, pp(polygon)))
    #for i, polygon in enumerate(new_isoband):
    #    print('debug: OUTPUT {0} {1}'.format(i, pp(polygon)))
            
    return new_isoband
