#[cfg(not(target_arch = "wasm32"))]
use pyo3::prelude::*;
#[cfg(target_arch = "wasm32")]
use serde::Deserialize;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

type Point = (f64, f64);
type Rect = (f64, f64, f64, f64);
type Segment = (Point, Point);

/// Uniform spatial index for trace segments.  Candidate leaders only need to
/// consider segments within their 20-pixel clearance envelope; indexing avoids
/// repeatedly scanning every curve segment for every candidate.
struct SegmentIndex {
    segments: Vec<Segment>,
    cells: HashMap<(i32, i32), Vec<usize>>,
}

impl SegmentIndex {
    const CELL_SIZE: f64 = 64.0;
    const SEARCH_CLEARANCE: f64 = 20.0;

    fn new(segments: Vec<Segment>) -> Self {
        let mut cells: HashMap<(i32, i32), Vec<usize>> = HashMap::new();
        for (index, segment) in segments.iter().enumerate() {
            let (min_x, max_x) = (
                segment.0 .0.min(segment.1 .0),
                segment.0 .0.max(segment.1 .0),
            );
            let (min_y, max_y) = (
                segment.0 .1.min(segment.1 .1),
                segment.0 .1.max(segment.1 .1),
            );
            for x in Self::cells(
                min_x - Self::SEARCH_CLEARANCE,
                max_x + Self::SEARCH_CLEARANCE,
            ) {
                for y in Self::cells(
                    min_y - Self::SEARCH_CLEARANCE,
                    max_y + Self::SEARCH_CLEARANCE,
                ) {
                    cells.entry((x, y)).or_default().push(index);
                }
            }
        }
        Self { segments, cells }
    }

    fn cells(minimum: f64, maximum: f64) -> std::ops::RangeInclusive<i32> {
        (minimum / Self::CELL_SIZE).floor() as i32..=(maximum / Self::CELL_SIZE).floor() as i32
    }

    fn nearby(&self, segment: Segment) -> Vec<&Segment> {
        let min_x = segment.0 .0.min(segment.1 .0) - Self::SEARCH_CLEARANCE;
        let max_x = segment.0 .0.max(segment.1 .0) + Self::SEARCH_CLEARANCE;
        let min_y = segment.0 .1.min(segment.1 .1) - Self::SEARCH_CLEARANCE;
        let max_y = segment.0 .1.max(segment.1 .1) + Self::SEARCH_CLEARANCE;
        let mut seen = HashSet::new();
        let mut nearby = Vec::new();
        for x in Self::cells(min_x, max_x) {
            for y in Self::cells(min_y, max_y) {
                if let Some(indices) = self.cells.get(&(x, y)) {
                    for index in indices {
                        if seen.insert(*index) {
                            nearby.push(&self.segments[*index]);
                        }
                    }
                }
            }
        }
        nearby
    }
}

const TRACE_CLEARANCE: f64 = 14.0;
const LEADER_START_CLEARANCE: f64 = 12.0;
const LEADER_TRACE_CLEARANCE: f64 = 3.0;
const MIN_LEADER_LENGTH: f64 = 48.0;
const GRID_ALIGNMENT_TOLERANCE: f64 = 8.0;
const GRID_ALIGNMENT_WEIGHT: f64 = 0.35;

#[derive(Clone)]
struct Request {
    key: String,
    x: f64,
    y: f64,
    yref: String,
    text: String,
    priority: i64,
    lanes: Vec<String>,
    direction: Option<String>,
}

fn rect_from_center(center: Point, size: Point) -> Rect {
    (
        center.0 - size.0 / 2.0,
        center.1 - size.1 / 2.0,
        center.0 + size.0 / 2.0,
        center.1 + size.1 / 2.0,
    )
}

fn expand_rect(rect: Rect, amount: f64) -> Rect {
    (
        rect.0 - amount,
        rect.1 - amount,
        rect.2 + amount,
        rect.3 + amount,
    )
}

fn rect_overlap(first: Rect, second: Rect) -> f64 {
    (first.2.min(second.2) - first.0.max(second.0)).max(0.0)
        * (first.3.min(second.3) - first.1.max(second.1)).max(0.0)
}

fn point_in_rect(point: Point, rect: Rect) -> bool {
    point.0 > rect.0 && point.0 < rect.2 && point.1 > rect.1 && point.1 < rect.3
}

fn point_in_or_on_rect(point: Point, rect: Rect) -> bool {
    point.0 >= rect.0 && point.0 <= rect.2 && point.1 >= rect.1 && point.1 <= rect.3
}

fn cross(first: Point, second: Point, third: Point) -> f64 {
    (second.0 - first.0) * (third.1 - first.1) - (second.1 - first.1) * (third.0 - first.0)
}

fn between(value: f64, first: f64, second: f64) -> bool {
    value >= first.min(second) - 0.001 && value <= first.max(second) + 0.001
}

fn segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool {
    let first_cross = cross(first_start, first_end, second_start);
    let second_cross = cross(first_start, first_end, second_end);
    let third_cross = cross(second_start, second_end, first_start);
    let fourth_cross = cross(second_start, second_end, first_end);
    let first_proper =
        (first_cross > 0.0 && second_cross < 0.0) || (first_cross < 0.0 && second_cross > 0.0);
    let second_proper =
        (third_cross > 0.0 && fourth_cross < 0.0) || (third_cross < 0.0 && fourth_cross > 0.0);
    (first_proper && second_proper)
        || (first_cross.abs() < 0.001
            && between(second_start.0, first_start.0, first_end.0)
            && between(second_start.1, first_start.1, first_end.1))
        || (second_cross.abs() < 0.001
            && between(second_end.0, first_start.0, first_end.0)
            && between(second_end.1, first_start.1, first_end.1))
        || (third_cross.abs() < 0.001
            && between(first_start.0, second_start.0, second_end.0)
            && between(first_start.1, second_start.1, second_end.1))
        || (fourth_cross.abs() < 0.001
            && between(first_end.0, second_start.0, second_end.0)
            && between(first_end.1, second_start.1, second_end.1))
}

fn segment_intersects_rect(start: Point, end: Point, rect: Rect) -> bool {
    point_in_or_on_rect(start, rect)
        || point_in_or_on_rect(end, rect)
        || [
            ((rect.0, rect.1), (rect.2, rect.1)),
            ((rect.2, rect.1), (rect.2, rect.3)),
            ((rect.2, rect.3), (rect.0, rect.3)),
            ((rect.0, rect.3), (rect.0, rect.1)),
        ]
        .iter()
        .any(|(edge_start, edge_end)| segments_intersect(start, end, *edge_start, *edge_end))
}

fn point_to_segment_distance(point: Point, start: Point, end: Point) -> f64 {
    let dx = end.0 - start.0;
    let dy = end.1 - start.1;
    let length_squared = dx * dx + dy * dy;
    if length_squared == 0.0 {
        return (point.0 - start.0).hypot(point.1 - start.1);
    }
    let fraction =
        (((point.0 - start.0) * dx + (point.1 - start.1) * dy) / length_squared).clamp(0.0, 1.0);
    (point.0 - (start.0 + fraction * dx)).hypot(point.1 - (start.1 + fraction * dy))
}

fn segment_distance(first: Segment, second: Segment) -> f64 {
    if segments_intersect(first.0, first.1, second.0, second.1) {
        return 0.0;
    }
    point_to_segment_distance(first.0, second.0, second.1)
        .min(point_to_segment_distance(first.1, second.0, second.1))
        .min(point_to_segment_distance(second.0, first.0, first.1))
        .min(point_to_segment_distance(second.1, first.0, first.1))
}

fn leader_segment(anchor: Point, center: Point) -> Option<Segment> {
    let length = (center.0 - anchor.0).hypot(center.1 - anchor.1);
    if length <= LEADER_START_CLEARANCE {
        return None;
    }
    let fraction = LEADER_START_CLEARANCE / length;
    Some((
        (
            anchor.0 + (center.0 - anchor.0) * fraction,
            anchor.1 + (center.1 - anchor.1) * fraction,
        ),
        center,
    ))
}

fn leader_crosses_trace(anchor: Point, center: Point, segments: &[Segment]) -> bool {
    let Some(leader) = leader_segment(anchor, center) else {
        return true;
    };
    segments
        .iter()
        .any(|segment| segment_distance(leader, *segment) <= LEADER_TRACE_CLEARANCE)
}

fn leader_crosses_indexed_trace(anchor: Point, center: Point, index: &SegmentIndex) -> bool {
    let Some(leader) = leader_segment(anchor, center) else {
        return true;
    };
    index
        .nearby(leader)
        .iter()
        .any(|segment| segment_distance(leader, **segment) <= LEADER_TRACE_CLEARANCE)
}

fn leader_indexed_curve_penalty(anchor: Point, center: Point, index: &SegmentIndex) -> f64 {
    let Some(leader) = leader_segment(anchor, center) else {
        return 1000.0;
    };
    index
        .nearby(leader)
        .iter()
        .map(|segment| {
            let distance = segment_distance(leader, **segment);
            if distance <= LEADER_TRACE_CLEARANCE {
                100.0
            } else if distance < 20.0 {
                20.0 - distance
            } else {
                0.0
            }
        })
        .sum()
}

fn value_to_pixel(value: f64, range: Point, start: f64, end: f64) -> f64 {
    if range.0 == range.1 {
        return (start + end) / 2.0;
    }
    start + (value - range.0) / (range.1 - range.0) * (end - start)
}

fn curve_penalty(rect: Rect, points: &[Point], index: &SegmentIndex) -> Option<f64> {
    let clearance = expand_rect(rect, TRACE_CLEARANCE);
    let mut penalty = 0.0;
    for point in points {
        let point_rect = rect_from_center(*point, (5.0, 5.0));
        if rect_overlap(rect, point_rect) > 0.0 {
            return None;
        }
        if rect_overlap(clearance, point_rect) > 0.0 {
            penalty += 20.0;
        }
    }
    for segment in index.nearby(((rect.0, rect.1), (rect.2, rect.3))) {
        if segment_intersects_rect(segment.0, segment.1, rect) {
            return None;
        }
        if segment_intersects_rect(segment.0, segment.1, clearance) {
            penalty += 20.0;
        }
    }
    Some(penalty)
}

fn direction_penalty(direction: &Option<String>, anchor: Point, center: Point) -> f64 {
    match direction.as_deref() {
        Some("above") if center.1 >= anchor.1 => 1000.0 + center.1 - anchor.1,
        Some("below") if center.1 <= anchor.1 => 1000.0 + anchor.1 - center.1,
        _ => 0.0,
    }
}

fn grid_alignment_penalty(rect: Rect, x_lines: &[f64], y_lines: &[f64]) -> f64 {
    fn axis_penalty(edges: [f64; 3], lines: &[f64]) -> f64 {
        if lines.is_empty() {
            return 0.0;
        }
        let distance = edges
            .iter()
            .flat_map(|edge| lines.iter().map(move |line| (edge - line).abs()))
            .fold(f64::INFINITY, f64::min);
        (distance - GRID_ALIGNMENT_TOLERANCE).max(0.0)
    }
    GRID_ALIGNMENT_WEIGHT
        * (axis_penalty([rect.0, (rect.0 + rect.2) / 2.0, rect.2], x_lines)
            + axis_penalty([rect.1, (rect.1 + rect.3) / 2.0, rect.3], y_lines))
}

fn lanes() -> [(&'static str, f64); 5] {
    [
        ("top", 0.12),
        ("upper", 0.28),
        ("middle", 0.50),
        ("lower", 0.70),
        ("bottom", 0.86),
    ]
}

fn candidates(
    request: &Request,
    anchor: Point,
    size: Point,
    plot: Rect,
    grid_x: &[f64],
    grid_y: &[f64],
) -> Vec<(Point, i64)> {
    let (left, top, right, bottom) = plot;
    let x_min = left + size.0 / 2.0 + 5.0;
    let x_max = right - size.0 / 2.0 - 5.0;
    let y_min = top + size.1 / 2.0 + 5.0;
    let y_max = bottom - size.1 / 2.0 - 5.0;
    if x_min > x_max || y_min > y_max {
        return vec![];
    }
    let mut result: Vec<(Point, i64)> = Vec::new();
    let mut add = |center: Point, rank: i64| {
        let clamped = (center.0.clamp(x_min, x_max), center.1.clamp(y_min, y_max));
        if !result.iter().any(|(other, _)| {
            other.0.round() == clamped.0.round() && other.1.round() == clamped.1.round()
        }) {
            result.push((clamped, rank));
        }
    };
    let lane_names: Vec<&str> = request
        .lanes
        .iter()
        .map(String::as_str)
        .chain(
            lanes()
                .iter()
                .map(|(name, _)| *name)
                .filter(|name| !request.lanes.iter().any(|lane| lane == name)),
        )
        .collect();
    let offset = MIN_LEADER_LENGTH.max(size.1 / 2.0 + TRACE_CLEARANCE + 6.0);
    for (index, (dx, dy)) in [
        (0.0, -offset),
        (0.0, offset),
        (-48.0, -offset),
        (48.0, -offset),
        (-48.0, offset),
        (48.0, offset),
        (0.0, -2.0 * offset),
        (0.0, 2.0 * offset),
        (-96.0, -2.0 * offset),
        (96.0, -2.0 * offset),
        (-96.0, 2.0 * offset),
        (96.0, 2.0 * offset),
    ]
    .iter()
    .enumerate()
    {
        add(
            (anchor.0 + dx, anchor.1 + dy),
            lane_names.len() as i64 + index as i64,
        );
    }
    for x in grid_x {
        for center_x in [*x, *x - size.0 / 2.0, *x + size.0 / 2.0] {
            for center_y in [
                anchor.1 - offset,
                anchor.1 + offset,
                anchor.1 - 2.0 * offset,
                anchor.1 + 2.0 * offset,
            ] {
                add((center_x, center_y), 1);
            }
        }
    }
    for y in grid_y {
        for center_y in [*y, *y - size.1 / 2.0, *y + size.1 / 2.0] {
            for center_x in [
                anchor.0,
                anchor.0 - 48.0,
                anchor.0 + 48.0,
                anchor.0 - 96.0,
                anchor.0 + 96.0,
            ] {
                add((center_x, center_y), 1);
            }
        }
    }
    for (rank, name) in lane_names.iter().enumerate() {
        if let Some((_, fraction)) = lanes().iter().find(|(lane, _)| lane == name) {
            for dx in [0.0, -100.0, 100.0, -190.0, 190.0] {
                add(
                    (anchor.0 + dx, top + fraction * (bottom - top)),
                    rank as i64,
                );
            }
        }
    }
    result
}

#[allow(clippy::too_many_arguments, clippy::type_complexity)]
fn place_annotations(
    raw_requests: Vec<(
        String,
        f64,
        f64,
        String,
        String,
        i64,
        Vec<String>,
        Option<String>,
    )>,
    width: f64,
    height: f64,
    margin: (f64, f64, f64, f64),
    x_range: (f64, f64),
    y_ranges: Vec<(String, f64, f64)>,
    x_scale_log: bool,
    font_size: f64,
    label_pad: f64,
    x_domain: (f64, f64),
    y_domain: (f64, f64),
    grid_x: Vec<f64>,
    grid_y: Vec<(String, Vec<f64>)>,
    trace_points: Vec<(f64, f64, String)>,
    reserved: Vec<Rect>,
    trace_segments: Vec<(f64, f64, f64, f64, String, Option<String>)>,
) -> Vec<(Option<Point>, bool)> {
    let requests: Vec<Request> = raw_requests
        .into_iter()
        .map(
            |(key, x, y, yref, text, priority, lanes, direction)| Request {
                key,
                x,
                y,
                yref,
                text,
                priority,
                lanes,
                direction,
            },
        )
        .collect();
    let inner_right = width - margin.1;
    let inner_bottom = height - margin.3;
    let plot = (
        margin.0 + x_domain.0 * (inner_right - margin.0),
        margin.2 + (1.0 - y_domain.1) * (inner_bottom - margin.2),
        margin.0 + x_domain.1 * (inner_right - margin.0),
        margin.2 + (1.0 - y_domain.0) * (inner_bottom - margin.2),
    );
    let ranges: HashMap<String, Point> = y_ranges
        .into_iter()
        .map(|(axis, min, max)| (axis, (min, max)))
        .collect();
    let grid_y: HashMap<String, Vec<f64>> = grid_y
        .into_iter()
        .map(|(axis, values)| {
            let range = *ranges
                .get(&axis)
                .expect("grid axis must have a corresponding range");
            (
                axis,
                values
                    .into_iter()
                    .map(|value| value_to_pixel(value, range, plot.3, plot.1))
                    .collect(),
            )
        })
        .collect();
    let grid_x: Vec<f64> = grid_x
        .into_iter()
        .map(|value| value_to_pixel(value, x_range, plot.0, plot.2))
        .collect();
    let mut points: HashMap<String, Vec<Point>> = HashMap::new();
    let mut axis_segments: HashMap<String, Vec<Segment>> = HashMap::new();
    let mut curve_segments: HashMap<(String, String), Vec<Segment>> = HashMap::new();
    let mut all_segments = Vec::new();
    for (x, y, axis) in trace_points {
        if let Some(range) = ranges.get(&axis) {
            let xv = if x_scale_log && x > 0.0 { x.log10() } else { x };
            if xv.is_finite() && y.is_finite() {
                let point = (
                    value_to_pixel(xv, x_range, plot.0, plot.2),
                    value_to_pixel(y, *range, plot.3, plot.1),
                );
                if point.0 >= plot.0 && point.0 <= plot.2 && point.1 >= plot.1 && point.1 <= plot.3
                {
                    points.entry(axis).or_default().push(point);
                }
            }
        }
    }
    for (x1, y1, x2, y2, axis, key) in trace_segments {
        if ranges.contains_key(&axis) && [x1, y1, x2, y2].iter().all(|value| value.is_finite()) {
            let segment = ((x1, y1), (x2, y2));
            axis_segments.entry(axis.clone()).or_default().push(segment);
            all_segments.push(segment);
            if let Some(key) = key {
                curve_segments.entry((axis, key)).or_default().push(segment);
            }
        }
    }
    let all_points: Vec<Point> = points.values().flatten().copied().collect();
    let axis_segment_indexes: HashMap<String, SegmentIndex> = axis_segments
        .iter()
        .map(|(axis, segments)| (axis.clone(), SegmentIndex::new(segments.clone())))
        .collect();
    let all_segment_index = SegmentIndex::new(all_segments);
    let mut order: Vec<usize> = (0..requests.len()).collect();
    order.sort_by(|first, second| {
        let a = &requests[*first];
        let b = &requests[*second];
        match (a.direction.as_deref(), b.direction.as_deref()) {
            (Some("above"), Some("above")) | (Some("below"), Some("below")) => {
                a.x.partial_cmp(&b.x).unwrap_or(Ordering::Equal)
            }
            _ => b.priority.cmp(&a.priority),
        }
    });
    let mut occupied = Vec::new();
    let mut arrows: Vec<Segment> = Vec::new();
    let mut output: Vec<(Option<Point>, bool)> = vec![(None, true); requests.len()];
    for index in order {
        let request = &requests[index];
        let Some(y_range) = ranges.get(&request.yref) else {
            continue;
        };
        let anchor = (
            value_to_pixel(request.x, x_range, plot.0, plot.2),
            value_to_pixel(request.y, *y_range, plot.3, plot.1),
        );
        let line_count = request.text.split("<br>").count() as f64;
        let longest_line = request
            .text
            .split("<br>")
            .map(|line| line.chars().count())
            .max()
            .unwrap_or(1) as f64;
        let size = (
            longest_line * font_size * 0.62 + 2.0 * label_pad + 2.0,
            line_count * font_size * 1.35 + 2.0 * label_pad + 2.0,
        );
        let candidates = candidates(
            request,
            anchor,
            size,
            plot,
            &grid_x,
            grid_y.get(&request.yref).map(Vec::as_slice).unwrap_or(&[]),
        );
        let axis = axis_segments
            .get(&request.yref)
            .map(Vec::as_slice)
            .unwrap_or(&[]);
        let own = curve_segments
            .get(&(request.yref.clone(), request.key.clone()))
            .map(Vec::as_slice)
            .unwrap_or(axis);
        let mut best = None;
        for global in [true, false] {
            let mut phase = None;
            for (center, rank) in &candidates {
                let rect = rect_from_center(*center, size);
                let distance = (center.0 - anchor.0).hypot(center.1 - anchor.1);
                // Python's floating-point distance lands just below 48 for
                // exact local offsets.  Treat the boundary consistently so
                // native and fallback placement select the same candidate.
                if distance <= MIN_LEADER_LENGTH
                    || direction_penalty(&request.direction, anchor, *center) > 0.0
                    || rect.0 < plot.0
                    || rect.2 > plot.2
                    || rect.1 < plot.1
                    || rect.3 > plot.3
                    || occupied
                        .iter()
                        .any(|other| rect_overlap(rect, *other) > 0.0)
                    || reserved
                        .iter()
                        .any(|other| rect_overlap(rect, *other) > 0.0)
                    || arrows
                        .iter()
                        .any(|arrow| segments_intersect(anchor, *center, arrow.0, arrow.1))
                    || occupied.iter().any(|other| {
                        !point_in_rect(anchor, *other)
                            && segment_intersects_rect(anchor, *center, *other)
                    })
                    || arrows.iter().any(|arrow| {
                        !point_in_rect(arrow.0, rect)
                            && segment_intersects_rect(arrow.0, arrow.1, rect)
                    })
                {
                    continue;
                }
                let leader_score = if global {
                    if leader_crosses_indexed_trace(anchor, *center, &all_segment_index) {
                        continue;
                    }
                    0.0
                } else {
                    if leader_crosses_trace(anchor, *center, own) {
                        continue;
                    }
                    leader_indexed_curve_penalty(anchor, *center, &all_segment_index)
                };
                let cross_axis = request.yref == "y2";
                let curve_points = if cross_axis {
                    &all_points
                } else {
                    points.get(&request.yref).map(Vec::as_slice).unwrap_or(&[])
                };
                let curve_index = if cross_axis {
                    &all_segment_index
                } else {
                    axis_segment_indexes
                        .get(&request.yref)
                        .unwrap_or(&all_segment_index)
                };
                let Some(curve) = curve_penalty(rect, curve_points, curve_index) else {
                    continue;
                };
                let score = distance
                    + *rank as f64 * 2.0
                    + curve
                    + leader_score
                    + grid_alignment_penalty(
                        rect,
                        &grid_x,
                        grid_y.get(&request.yref).map(Vec::as_slice).unwrap_or(&[]),
                    );
                if phase.as_ref().map_or(true, |(old, _, _)| score < *old) {
                    phase = Some((score, *center, rect));
                }
            }
            if phase.is_some() {
                best = phase;
                break;
            }
        }
        if let Some((_, center, rect)) = best {
            occupied.push(rect);
            arrows.push((anchor, center));
            output[index] = (Some(center), false);
        }
    }
    output
}

#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
#[allow(clippy::too_many_arguments, clippy::type_complexity)]
fn c_place_annotations(
    raw_requests: Vec<(
        String,
        f64,
        f64,
        String,
        String,
        i64,
        Vec<String>,
        Option<String>,
    )>,
    width: f64,
    height: f64,
    margin: (f64, f64, f64, f64),
    x_range: (f64, f64),
    y_ranges: Vec<(String, f64, f64)>,
    x_scale_log: bool,
    font_size: f64,
    label_pad: f64,
    x_domain: (f64, f64),
    y_domain: (f64, f64),
    grid_x: Vec<f64>,
    grid_y: Vec<(String, Vec<f64>)>,
    trace_points: Vec<(f64, f64, String)>,
    reserved: Vec<Rect>,
    trace_segments: Vec<(f64, f64, f64, f64, String, Option<String>)>,
) -> Vec<(Option<Point>, bool)> {
    place_annotations(
        raw_requests,
        width,
        height,
        margin,
        x_range,
        y_ranges,
        x_scale_log,
        font_size,
        label_pad,
        x_domain,
        y_domain,
        grid_x,
        grid_y,
        trace_points,
        reserved,
        trace_segments,
    )
}

#[cfg(target_arch = "wasm32")]
#[derive(Deserialize)]
struct WasmInput {
    raw_requests: Vec<(
        String,
        f64,
        f64,
        String,
        String,
        i64,
        Vec<String>,
        Option<String>,
    )>,
    width: f64,
    height: f64,
    margin: (f64, f64, f64, f64),
    x_range: (f64, f64),
    y_ranges: Vec<(String, f64, f64)>,
    x_scale_log: bool,
    font_size: f64,
    label_pad: f64,
    x_domain: (f64, f64),
    y_domain: (f64, f64),
    grid_x: Vec<f64>,
    grid_y: Vec<(String, Vec<f64>)>,
    trace_points: Vec<(f64, f64, String)>,
    reserved: Vec<Rect>,
    trace_segments: Vec<(f64, f64, f64, f64, String, Option<String>)>,
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn solve_annotations(input: JsValue) -> Result<JsValue, JsValue> {
    let input: WasmInput = serde_wasm_bindgen::from_value(input)
        .map_err(|error| JsValue::from_str(&error.to_string()))?;
    let output = place_annotations(
        input.raw_requests,
        input.width,
        input.height,
        input.margin,
        input.x_range,
        input.y_ranges,
        input.x_scale_log,
        input.font_size,
        input.label_pad,
        input.x_domain,
        input.y_domain,
        input.grid_x,
        input.grid_y,
        input.trace_points,
        input.reserved,
        input.trace_segments,
    );
    serde_wasm_bindgen::to_value(&output).map_err(|error| JsValue::from_str(&error.to_string()))
}

#[cfg(not(target_arch = "wasm32"))]
#[pymodule]
fn annotations_rust(_py: Python, module: &Bound<PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(c_place_annotations, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn curve_penalty_rejects_a_cross_axis_curve() {
        let primary_axis = SegmentIndex::new(vec![((50.0, 212.0), (750.0, 212.0))]);
        assert!(curve_penalty((300.0, 200.0, 500.0, 225.0), &[], &primary_axis).is_none());
    }
}
