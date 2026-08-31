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
type RawRequest = (
    String,
    f64,
    f64,
    String,
    String,
    i64,
    Vec<String>,
    Option<String>,
);

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
const LEADER_COMFORT_CLEARANCE: f64 = 20.0;
const LEADER_CROSSING_PENALTY: f64 = 10_000.0;
const MIN_LEADER_LENGTH: f64 = 48.0;
const PREFERRED_MAX_LEADER_LENGTH: f64 = 260.0;
const MIN_HORIZONTAL_LEADER_OFFSET: f64 = 24.0;
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
                LEADER_CROSSING_PENALTY
            } else if distance < LEADER_COMFORT_CLEARANCE {
                (LEADER_COMFORT_CLEARANCE - distance) * 4.0
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

#[cfg(any(test, target_arch = "wasm32"))]
fn normalize_wasm_request_x(requests: &mut [RawRequest], logarithmic: bool) {
    if !logarithmic {
        return;
    }
    for request in requests {
        if request.1 > 0.0 {
            request.1 = request.1.log10();
        }
    }
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

fn leader_geometry_penalty(anchor: Point, center: Point) -> f64 {
    // Plotly draws from the label at `center` to the curve at `anchor`.
    // Prefer the resulting down-right leader; horizontal remains acceptable.
    let dx = center.0 - anchor.0;
    let dy = center.1 - anchor.1;
    if dx.abs() < 12.0 {
        80.0
    } else if dy < 0.0 && dx < 0.0 {
        0.0
    } else if dy.abs() < 12.0 {
        12.0
    } else if dy < 0.0 {
        25.0
    } else {
        35.0
    }
}

/// A leader that leaves the label vertically is visually ambiguous and is
/// especially easy to mistake for a nearby curve.  Keep this separate from
/// scoring: it is a placement constraint, not merely a preference.
fn has_acceptable_leader_geometry(anchor: Point, center: Point) -> bool {
    (center.0 - anchor.0).abs() >= MIN_HORIZONTAL_LEADER_OFFSET
}

fn pending_anchor_penalty(
    center: Point,
    anchors: &[Option<Point>],
    placed: &[(Option<Point>, bool)],
    requests: &[Request],
    yref: &str,
    index: usize,
) -> f64 {
    anchors
        .iter()
        .enumerate()
        .filter_map(|(other_index, anchor)| {
            if other_index == index || !placed[other_index].1 || requests[other_index].yref != yref
            {
                return None;
            }
            let anchor = (*anchor)?;
            Some((180.0 - (center.0 - anchor.0).hypot(center.1 - anchor.1)).max(0.0) * 2.0)
        })
        .sum()
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
        // Near a plot edge an "above" candidate can be unavailable.  A
        // lateral leader is still much clearer than a vertical fallback.
        (-72.0, -16.0),
        (72.0, -16.0),
        (-120.0, -16.0),
        (120.0, -16.0),
        (-120.0, 24.0),
        (120.0, 24.0),
        (-168.0, -48.0),
        (168.0, -48.0),
        (-168.0, -16.0),
        (168.0, -16.0),
        (-168.0, 48.0),
        (168.0, 48.0),
        // Intermediate radial ring for the bounded search. These positions
        // let a previous label move around a blocked neighbour while keeping
        // the leader below the accepted 260-pixel limit.
        (-144.0, -96.0),
        (144.0, -96.0),
        (-144.0, 96.0),
        (144.0, 96.0),
        (-160.0, -64.0),
        (160.0, -64.0),
        (-160.0, 64.0),
        (160.0, 64.0),
        (-96.0, -144.0),
        (96.0, -144.0),
        (-96.0, 144.0),
        (96.0, 144.0),
        (-240.0, -72.0),
        (240.0, -72.0),
        (-240.0, -16.0),
        (240.0, -16.0),
        (-240.0, 72.0),
        (240.0, 72.0),
    ]
    .iter()
    .enumerate()
    {
        // Away from the top edge, retain strict "above" placement. The
        // lateral escape set is only for labels which cannot fit above their
        // anchor while remaining inside the frame.
        if request.direction.as_deref() == Some("above")
            && anchor.1 - y_min > offset
            && *dy > -offset
        {
            continue;
        }
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
            for dx in [
                0.0, -100.0, 100.0, -190.0, 190.0, -280.0, 280.0, -360.0, 360.0,
            ] {
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
    raw_requests: Vec<RawRequest>,
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
    let mut output: Vec<(Option<Point>, bool)> = vec![(None, true); requests.len()];
    let anchors: Vec<Option<Point>> = requests
        .iter()
        .map(|request| {
            ranges.get(&request.yref).map(|range| {
                (
                    value_to_pixel(request.x, x_range, plot.0, plot.2),
                    value_to_pixel(request.y, *range, plot.3, plot.1),
                )
            })
        })
        .collect();
    let mut occupied = Vec::new();
    let mut arrows: Vec<Segment> = Vec::new();
    for &index in &order {
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
                    || distance > PREFERRED_MAX_LEADER_LENGTH
                    || !has_acceptable_leader_geometry(anchor, *center)
                    || (request.direction.as_deref() == Some("above")
                        && anchor.1 - plot.1 > MIN_LEADER_LENGTH + size.1 / 2.0 + 5.0
                        && direction_penalty(&request.direction, anchor, *center) > 0.0)
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
                    leader_indexed_curve_penalty(anchor, *center, &all_segment_index)
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
                    + leader_geometry_penalty(anchor, *center)
                    + direction_penalty(&request.direction, anchor, *center)
                    // Preserve space around annotations that have not been
                    // placed yet, so the greedy pass has limited look-ahead.
                    + pending_anchor_penalty(
                        *center,
                        &anchors,
                        &output,
                        &requests,
                        &request.yref,
                        index,
                    )
                    + curve
                    + leader_score
                    + grid_alignment_penalty(
                        rect,
                        &grid_x,
                        grid_y.get(&request.yref).map(Vec::as_slice).unwrap_or(&[]),
                    );
                if phase.as_ref().is_none_or(|(old, _, _)| score < *old) {
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

    // The greedy pass is intentionally cheap and is sufficient for almost
    // every chart.  If it hides a label, retry with a bounded beam search so
    // an early locally-good choice can be moved out of a later label's way.
    if output.iter().any(|(_, hidden)| *hidden) {
        const BEAM_WIDTH: usize = 128;
        const CANDIDATES_PER_STATE: usize = 24;

        #[derive(Clone)]
        struct SearchState {
            occupied: Vec<Rect>,
            arrows: Vec<Segment>,
            output: Vec<(Option<Point>, bool)>,
            score: f64,
            hidden_count: usize,
        }

        let mut states = vec![SearchState {
            occupied: Vec::new(),
            arrows: Vec::new(),
            output: vec![(None, true); requests.len()],
            score: 0.0,
            hidden_count: 0,
        }];

        for &index in &order {
            let request = &requests[index];
            let Some(y_range) = ranges.get(&request.yref) else {
                for state in &mut states {
                    state.hidden_count += 1;
                }
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
            let request_candidates = candidates(
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
            let mut next_states = Vec::new();

            for state in &states {
                let mut choices = Vec::new();
                for global in [true, false] {
                    let mut phase = Vec::new();
                    for (center, rank) in &request_candidates {
                        let rect = rect_from_center(*center, size);
                        let distance = (center.0 - anchor.0).hypot(center.1 - anchor.1);
                        // The greedy pass enforces the preferred 260-pixel
                        // leader limit. Recovery owns the former JavaScript
                        // fallback policy, so it may use any in-frame candidate
                        // rather than hiding a label and solving everything a
                        // second time in JavaScript.
                        if distance <= MIN_LEADER_LENGTH
                            || !has_acceptable_leader_geometry(anchor, *center)
                            || rect.0 < plot.0
                            || rect.2 > plot.2
                            || rect.1 < plot.1
                            || rect.3 > plot.3
                            || state
                                .occupied
                                .iter()
                                .any(|other| rect_overlap(rect, *other) > 0.0)
                            || reserved
                                .iter()
                                .any(|other| rect_overlap(rect, *other) > 0.0)
                            || state
                                .arrows
                                .iter()
                                .any(|arrow| segments_intersect(anchor, *center, arrow.0, arrow.1))
                            || state.occupied.iter().any(|other| {
                                !point_in_rect(anchor, *other)
                                    && segment_intersects_rect(anchor, *center, *other)
                            })
                            || state.arrows.iter().any(|arrow| {
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
                            leader_indexed_curve_penalty(anchor, *center, &all_segment_index)
                        } else {
                            if leader_crosses_trace(anchor, *center, own) {
                                continue;
                            }
                            leader_indexed_curve_penalty(anchor, *center, &all_segment_index)
                        };
                        let Some(curve) = curve_penalty(rect, curve_points, curve_index) else {
                            continue;
                        };
                        let score = distance
                            + *rank as f64 * 2.0
                            + leader_geometry_penalty(anchor, *center)
                            // In recovery, direction is a strong preference
                            // rather than a constraint that can force static
                            // fallback for the entire annotation set.
                            + direction_penalty(&request.direction, anchor, *center).min(250.0)
                            + pending_anchor_penalty(
                                *center,
                                &anchors,
                                &state.output,
                                &requests,
                                &request.yref,
                                index,
                            )
                            + curve
                            + leader_score
                            + grid_alignment_penalty(
                                rect,
                                &grid_x,
                                grid_y.get(&request.yref).map(Vec::as_slice).unwrap_or(&[]),
                            );
                        phase.push((score, *center, rect));
                    }
                    if !phase.is_empty() {
                        choices = phase;
                        break;
                    }
                }

                choices.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
                choices.truncate(CANDIDATES_PER_STATE);
                for (choice_score, center, rect) in choices {
                    let mut next = state.clone();
                    next.occupied.push(rect);
                    next.arrows.push((anchor, center));
                    next.output[index] = (Some(center), false);
                    next.score += choice_score;
                    next_states.push(next);
                }

                // Keep a hidden branch so the search always has a result;
                // hidden_count is compared before score, so it only wins when
                // every placement branch is impossible later.
                let mut hidden = state.clone();
                hidden.hidden_count += 1;
                next_states.push(hidden);
            }

            next_states.sort_by(|a, b| {
                a.hidden_count
                    .cmp(&b.hidden_count)
                    .then_with(|| a.score.partial_cmp(&b.score).unwrap_or(Ordering::Equal))
            });
            next_states.truncate(BEAM_WIDTH);
            states = next_states;
        }

        if let Some(best) = states.into_iter().min_by(|a, b| {
            a.hidden_count
                .cmp(&b.hidden_count)
                .then_with(|| a.score.partial_cmp(&b.score).unwrap_or(Ordering::Equal))
        }) {
            let greedy_hidden = output.iter().filter(|(_, hidden)| *hidden).count();
            if best.hidden_count < greedy_hidden {
                output = best.output;
            }
        }
    }
    output
}

#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
#[allow(clippy::too_many_arguments, clippy::type_complexity)]
fn c_place_annotations(
    raw_requests: Vec<RawRequest>,
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
    raw_requests: Vec<RawRequest>,
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
    let mut input: WasmInput = serde_wasm_bindgen::from_value(input)
        .map_err(|error| JsValue::from_str(&error.to_string()))?;
    normalize_wasm_request_x(&mut input.raw_requests, input.x_scale_log);
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
    fn rejects_vertical_leader_geometry() {
        let anchor = (400.0, 300.0);

        assert!(!has_acceptable_leader_geometry(anchor, (400.0, 240.0)));
        assert!(!has_acceptable_leader_geometry(anchor, (423.9, 252.0)));
        assert!(has_acceptable_leader_geometry(anchor, (352.0, 252.0)));
    }

    #[test]
    fn solver_selects_an_above_left_leader_when_the_plot_is_clear() {
        let output = place_annotations(
            vec![(
                "Listening Window".to_owned(),
                50.0,
                0.0,
                "y".to_owned(),
                "LW".to_owned(),
                0,
                vec![],
                None,
            )],
            900.0,
            600.0,
            (80.0, 50.0, 50.0, 50.0),
            (0.0, 100.0),
            vec![("y".to_owned(), -10.0, 10.0)],
            false,
            10.0,
            3.0,
            (0.0, 1.0),
            (0.0, 1.0),
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
        );
        let center = output[0].0.expect("clear plot should place its label");
        let anchor = (465.0, 300.0);

        assert!(has_acceptable_leader_geometry(anchor, center));
        assert!(center.0 < anchor.0 && center.1 < anchor.1);
    }

    #[test]
    fn solver_keeps_an_edge_label_nonvertical_when_above_is_impossible() {
        let output = place_annotations(
            vec![(
                "Listening Window".to_owned(),
                50.0,
                10.0,
                "y".to_owned(),
                "LW".to_owned(),
                0,
                vec!["top".to_owned()],
                Some("above".to_owned()),
            )],
            900.0,
            600.0,
            (80.0, 50.0, 50.0, 50.0),
            (0.0, 100.0),
            vec![("y".to_owned(), -10.0, 10.0)],
            false,
            10.0,
            3.0,
            (0.0, 1.0),
            (0.0, 1.0),
            vec![],
            vec![],
            vec![],
            vec![],
            vec![],
        );
        let center = output[0]
            .0
            .expect("an edge label should use a lateral fallback");
        let anchor = (465.0, 50.0);

        assert!(has_acceptable_leader_geometry(anchor, center));
    }

    #[test]
    fn solver_prefers_a_clear_leader_over_crossing_another_trace() {
        let traces = vec![
            (
                0.0,
                400.0,
                1_200.0,
                400.0,
                "y".to_owned(),
                Some("On Axis".to_owned()),
            ),
            (
                620.0,
                400.0,
                620.0,
                800.0,
                "y".to_owned(),
                Some("blocking".to_owned()),
            ),
        ];
        let trace_index = SegmentIndex::new(
            traces
                .iter()
                .map(|(x1, y1, x2, y2, _, _)| ((*x1, *y1), (*x2, *y2)))
                .collect(),
        );
        let output = place_annotations(
            vec![(
                "On Axis".to_owned(),
                50.0,
                0.0,
                "y".to_owned(),
                "clear leader".to_owned(),
                100,
                vec!["middle".to_owned()],
                Some("below".to_owned()),
            )],
            1_200.0,
            800.0,
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 100.0),
            vec![("y".to_owned(), -10.0, 10.0)],
            false,
            10.0,
            3.0,
            (0.0, 1.0),
            (0.0, 1.0),
            vec![],
            vec![],
            vec![],
            vec![],
            traces,
        );
        let anchor = (600.0, 400.0);
        let center = output[0].0.expect("a clear left-hand candidate exists");

        assert!(center.0 < anchor.0);
        assert!(center.1 > anchor.1);
        assert!(!leader_crosses_indexed_trace(anchor, center, &trace_index));
    }

    #[test]
    fn recovery_uses_a_long_in_frame_leader_before_hiding_a_label() {
        let output = place_annotations(
            vec![(
                "On Axis".to_owned(),
                50.0,
                0.0,
                "y".to_owned(),
                "long recovery".to_owned(),
                100,
                vec!["middle".to_owned()],
                None,
            )],
            1_200.0,
            800.0,
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 100.0),
            vec![("y".to_owned(), -10.0, 10.0)],
            false,
            10.0,
            3.0,
            (0.0, 1.0),
            (0.0, 1.0),
            vec![],
            vec![],
            vec![],
            vec![(330.0, 0.0, 870.0, 800.0)],
            vec![],
        );
        let anchor = (600.0, 400.0);
        let center = output[0]
            .0
            .expect("Rust recovery should use a longer candidate before hiding the label");

        assert!(!output[0].1);
        assert!((center.0 - anchor.0).hypot(center.1 - anchor.1) > PREFERRED_MAX_LEADER_LENGTH);
    }

    #[test]
    fn curve_penalty_rejects_a_cross_axis_curve() {
        let primary_axis = SegmentIndex::new(vec![((50.0, 212.0), (750.0, 212.0))]);
        assert!(curve_penalty((300.0, 200.0, 500.0, 225.0), &[], &primary_axis).is_none());
    }

    #[test]
    fn clarity_66_layout_keeps_all_six_labels_visible() {
        let mut requests: Vec<RawRequest> = vec![
            (
                "On Axis",
                2_380.0,
                1.29,
                "y",
                "0.26 db/oct sm 0.76",
                100,
                vec!["top", "upper", "middle"],
                Some("above"),
            ),
            (
                "Listening Window",
                8_280.0,
                1.50,
                "y",
                "0.04 db/oct sm 0.80",
                95,
                vec!["top", "upper", "middle"],
                Some("above"),
            ),
            (
                "Early Reflections",
                10_000.0,
                -6.62,
                "y",
                "-0.76 db/oct sm 0.69",
                80,
                vec!["middle", "upper", "lower"],
                Some("below"),
            ),
            (
                "Sound Power",
                10_000.0,
                -10.97,
                "y",
                "-1.43 db/oct sm 0.62",
                75,
                vec!["upper", "middle", "lower"],
                Some("below"),
            ),
            (
                "Early Reflections DI",
                10_000.0,
                5.56,
                "y2",
                "0.79 db/oct sm 0.84",
                70,
                vec!["upper", "top", "middle", "lower", "bottom"],
                Some("below"),
            ),
            (
                "Sound Power DI",
                10_000.0,
                9.91,
                "y2",
                "1.46 db/oct sm 0.72",
                65,
                vec!["upper", "top", "middle", "lower", "bottom"],
                Some("above"),
            ),
        ]
        .into_iter()
        .map(|(key, x, y, yref, text, priority, lanes, direction)| {
            (
                key.to_owned(),
                x,
                y,
                yref.to_owned(),
                text.to_owned(),
                priority,
                lanes.into_iter().map(str::to_owned).collect(),
                direction.map(str::to_owned),
            )
        })
        .collect();
        normalize_wasm_request_x(&mut requests, true);
        let plot = (30.0, 100.0, 1_581.0, 966.0);
        let trace = |y: f64, range: Point, yref: &str, key: &str| {
            let py = value_to_pixel(y, range, plot.3, plot.1);
            (
                plot.0,
                py,
                plot.2,
                py,
                yref.to_owned(),
                Some(key.to_owned()),
            )
        };
        let traces = vec![
            trace(1.29, (-45.0, 5.0), "y", "On Axis"),
            trace(1.50, (-45.0, 5.0), "y", "Listening Window"),
            trace(-6.62, (-45.0, 5.0), "y", "Early Reflections"),
            trace(-10.97, (-45.0, 5.0), "y", "Sound Power"),
            trace(5.56, (-5.0, 45.0), "y2", "Early Reflections DI"),
            trace(9.91, (-5.0, 45.0), "y2", "Sound Power DI"),
        ];
        let output = place_annotations(
            requests,
            1_636.0,
            1_116.0,
            (30.0, 55.0, 100.0, 150.0),
            (20.0_f64.log10(), 20_000.0_f64.log10()),
            vec![("y".to_owned(), -45.0, 5.0), ("y2".to_owned(), -5.0, 45.0)],
            true,
            10.0,
            5.0,
            (0.0, 1.0),
            (0.0, 1.0),
            vec![],
            vec![],
            vec![],
            vec![],
            traces,
        );

        assert!(output.iter().all(|(_, hidden)| !hidden));
        let x_range = (20.0_f64.log10(), 20_000.0_f64.log10());
        let early_reflections_anchor = (
            value_to_pixel(10_000.0_f64.log10(), x_range, plot.0, plot.2),
            value_to_pixel(-6.62, (-45.0, 5.0), plot.3, plot.1),
        );
        let sound_power_anchor = (
            value_to_pixel(10_000.0_f64.log10(), x_range, plot.0, plot.2),
            value_to_pixel(-10.97, (-45.0, 5.0), plot.3, plot.1),
        );
        let early_reflections_center = output[2].0.expect("Early Reflections needs a label box");
        let sound_power_center = output[3].0.expect("Sound Power needs a label box");
        let early_reflections_di_anchor = (
            value_to_pixel(10_000.0_f64.log10(), x_range, plot.0, plot.2),
            value_to_pixel(5.56, (-5.0, 45.0), plot.3, plot.1),
        );
        let early_reflections_di_center =
            output[4].0.expect("Early Reflections DI needs a label box");
        let sound_power_leader = (sound_power_center.0 - sound_power_anchor.0)
            .hypot(sound_power_center.1 - sound_power_anchor.1);

        assert!(early_reflections_center.1 > early_reflections_anchor.1);
        assert!(early_reflections_center.1 < sound_power_anchor.1);
        assert!(early_reflections_di_center.1 > early_reflections_di_anchor.1);
        assert!(sound_power_leader < 100.0);
        assert!(output[5].0.is_some(), "Sound Power DI needs a label box");
    }
}
