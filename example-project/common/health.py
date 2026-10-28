#!/usr/bin/env python3

NUM_CRS_IN_REASON = 10


class HealthAggregationMethod:
    # 'divide': The score is calculated by averaging the health scores of the inividual instances.
    DIVIDE = 'divide'
    # 'equal': The score is determined by the lowest health score amongst all the instances.
    EQUAL = 'equal'


class Metric:
    def __init__(
            self,
            metric_weight: int,
            enum_weights: dict,
            health_agg_method: HealthAggregationMethod):
        self.metric_weight = metric_weight
        self.enum_weights = enum_weights
        self.health_agg_method = health_agg_method


class ObjectHealthScore:
    def __init__(
            self,
            object_name: str,
            health_score: int):
        self.object_name = object_name
        self.health_score = health_score


class MetricHealthScore:
    def __init__(
            self,
            metric_name: str,
            health_score: float,
            health_score_reason: str):
        self.metric_name = metric_name
        self.health_score = health_score
        self.health_score_reason = health_score_reason


class MetricHealthScores:
    def __init__(
            self,
            metric_name: str,
            health_scores: list[ObjectHealthScore],
            object_type: str = 'CR'):
        self.metric_name = metric_name
        self.object_type = object_type
        self.health_scores = health_scores


def calculate_health_score_per_metric(metrics: dict, metric_name: str, metric_value: str, reason: str):
    health_score = metrics[metric_name].enum_weights[metric_value]
    health_score_reason = f'Metric "{metric_name}", value: {metric_value}'
    if reason:
        health_score_reason += f', reason: {reason}'
    return health_score, health_score_reason


def calculate_agg_health_score_for_metric(object_health_scores: list[ObjectHealthScore], agg_method: HealthAggregationMethod, object_type: str = 'CR'):
    if any(object_health.health_score is None for object_health in object_health_scores):
        return None, ''
    object_health_scores.sort(key=lambda x: x.health_score)
    if agg_method == HealthAggregationMethod.DIVIDE:
        return agg_health_divide_method(object_health_scores, object_type)
    elif agg_method == HealthAggregationMethod.EQUAL:
        return agg_health_equal_method(object_health_scores, object_type)


def agg_health_divide_method(object_health_scores: list[ObjectHealthScore], object_type: str):
    health_score_reason = ''
    count = 0
    total_score = 0
    for object_health_score in object_health_scores:
        if object_health_score.health_score != 100:
            if count < NUM_CRS_IN_REASON:
                if health_score_reason:
                    health_score_reason += ", "
                health_score_reason += f'{object_health_score.object_name}'
            count += 1
        total_score += object_health_score.health_score
    if health_score_reason:
        health_score_reason = f'{object_type}s negatively impacting score: ' + health_score_reason
    if count > NUM_CRS_IN_REASON:
        health_score_reason += f' and {count - NUM_CRS_IN_REASON} more'
    return total_score / len(object_health_scores), health_score_reason


def agg_health_equal_method(object_health_scores: list[ObjectHealthScore], object_type: str):
    health_score_reason = ''
    count = 0
    min_score = object_health_scores[0].health_score

    for object_health_score in object_health_scores:
        if object_health_score.health_score != 100 and object_health_score.health_score == min_score:
            if count < NUM_CRS_IN_REASON:
                if health_score_reason:
                    health_score_reason += ", "
                health_score_reason += f'{object_health_score.object_name}'
            count += 1
    if health_score_reason:
        health_score_reason = f'{object_type}s negatively impacting score: ' + health_score_reason
    if count > NUM_CRS_IN_REASON:
        health_score_reason += f'and {count - NUM_CRS_IN_REASON} more'
    return min_score, health_score_reason


def calculate_overall_health_score(metrics: dict, metric_health_scores: list[MetricHealthScore]):
    sum_health_scores = 0
    sum_weights = 0
    health_score_reason = 'Breakdown:\n'
    for m_score in metric_health_scores:
        metric_weight = metrics[m_score.metric_name].metric_weight
        sum_health_scores += metric_weight * m_score.health_score
        sum_weights += metric_weight
        health_score_reason += f'Metric "{m_score.metric_name}", weight: {metric_weight}, score: {int(m_score.health_score)}, calculation method: {metrics[m_score.metric_name].health_agg_method}'
        if m_score.health_score_reason:
            health_score_reason += f', {m_score.health_score_reason}'
        health_score_reason += '\n'

    if sum_weights > 0:
        return int(sum_health_scores / sum_weights), health_score_reason
    return None, ''


def calculate_per_metric_agg_and_overall_health_score(metrics: dict[str, Metric], metric_health_scores: list[MetricHealthScores]):
    agg_health_scores = []
    for per_metric_health_scores in metric_health_scores:
        if len(per_metric_health_scores.health_scores) == 0:
            continue
        agg_health_score, agg_health_score_reason = calculate_agg_health_score_for_metric(per_metric_health_scores.health_scores,
                                                                                          metrics[per_metric_health_scores.metric_name].health_agg_method,
                                                                                          per_metric_health_scores.object_type)
        if agg_health_score is None:
            return None, ''
        agg_health_scores.append(MetricHealthScore(metric_name=per_metric_health_scores.metric_name, health_score=agg_health_score, health_score_reason=agg_health_score_reason))
    return calculate_overall_health_score(metrics, agg_health_scores)
