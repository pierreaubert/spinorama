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
    # print('debug p1={0} p2={1} on {2}'.format(poly1, poly2, segment))
    o1 = order_polygon(poly1, segment)
    c1 = is_close(poly1)
    o2 = order_polygon(poly2, segment)
    c2 = is_close(poly2)
    # print('debug o1={0} o2={1}'.format(o1, o2))
    m1 = [o1[k] for k in range(1, len(o1)-c1)] + [o1[0]]
    m2 = [o2[k] for k in range(len(o2)-1-c2, 0, -1)]
    # print('debug m1={0} + m2={1} + c={2}'.format(m1, m2, m1[0]))
    return m1 + m2


pp_known = {
    (0,0): 'p0',
    (1,0): 'p1',
    (1,1): 'p2',
    (0,1): 'p3',
    (-1,1): 'p4',
    (-1,0): 'p5',
}

def pp(poly):
    s = '['
    for i in poly:
        if i in pp_known:
            s += pp_known[i]
        else:
            s += '({0},{1})'.format(i[0], i[1])
        s += ', '
    s += ']'
    return s


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

    print('debug: segment_to_polygons segment:')
    for i in segment_to_polygons.keys():
        print('    {0}: {1}'.format(i, segment_to_polygons[i]))

    # reverse of above
    polygons_to_segment = {}
    for segment, polys in segment_to_polygons.items():
        if len(polys) == 2:
            p1 = polys[0]
            p2 = polys[1]
            polygons_to_segment[(p1, p2)] = [(segment[0], segment[1]),
                                             (segment[2], segment[3])]

    print('debug: polygons_to_segment:')
    for polys, segment in polygons_to_segment.items():
        print('    {0}: {1}'.format(polys, segment))

    pointer_polygons = {}
    count_connected = 0
    connected_polygons = {}
    print('debug: connected_polygons:')
    for c in segment_to_polygons.keys():
        len_c = len(segment_to_polygons[c])
        if len_c == 2:
            # polygons are connected
            p1 = segment_to_polygons[c][0]
            p2 = segment_to_polygons[c][1]
            print('debug c={0} p1={1} p2={2}'.format(c, p1, p2))
            if p1 in pointer_polygons:
                print('debug case1 add {1} to pp[{0}]'.format(p1, p2))
                connected_polygons[pointer_polygons[p1]].add(p2)
                pointer_polygons[p2] = pointer_polygons[p1]
            elif p2 in pointer_polygons:
                print('debug case2 add {0} to pp[{1}]'.format(p1, p2))
                connected_polygons[pointer_polygons[p2]].add(p1)
                pointer_polygons[p1] = pointer_polygons[p2]
            else:
                connected_polygons[count_connected] = set([p1, p2])
                pointer_polygons[p1] = count_connected
                pointer_polygons[p2] = count_connected
                print('debug case3 pp[{0}]={2} pp[{1}]={2}'.format(p1, p2, count_connected))
                count_connected += 1
        elif len_c > 2:
            print('Error more than 2 polygons connected to 1 edge')

    print('debug count connected {0}'.format(count_connected))
    print('debug pointer_polygons {0}'.format(pointer_polygons))
    print('debug connected_polygons')
    for cp_k, cp_v in connected_polygons.items():
        print('  {0} {1}'.format(cp_k, cp_v))

    if count_connected == 0:
        return isoband

    new_isoband = []
    for i, polyset in connected_polygons.items():
        prev_pointer = polyset.pop()
        current_polygon = isoband[prev_pointer]
        try:
            while 1:
                next_pointer = polyset.pop()
                common_segment = polygons_to_segment[(prev_pointer, next_pointer)]
                merged_polygon = merge_2polygons(current_polygon,
                                                 isoband[next_pointer],
                                                 common_segment)
                print('debug: current {0} next {1} merged {2}'.format(pp(current_polygon),
                                                                      pp(isoband[next_pointer]),
                                                                      pp(merged_polygon)))
                prev_pointer = next_pointer
                current_polygon = merged_polygon
        except KeyError:
            new_isoband.append(current_polygon)
    
    # need to iterate
    return new_isoband
