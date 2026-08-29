namespace DataStoryBuilder.Application.Stories;

public static class StoryDataDiffEvaluator
{
    private const string SemanticAuditLimitation =
        "Semantic assertions beyond explicit direction contradictions and the bounded material business-concept vocabulary are not verified by the current prose-only generated-story contract.";

    public static StoryDataDiffResult Evaluate(
        GeneratedExecutiveStory story,
        GroundedStoryPromptInput groundedInput)
    {
        ArgumentNullException.ThrowIfNull(story);
        ArgumentNullException.ThrowIfNull(groundedInput);

        var projected = StoryItemAuditProjector.Create(story, groundedInput);
        var numericalAudits = StoryNumericalAuditor.Audit(projected);
        var hasNumericalMismatch = numericalAudits.Any(audit => !audit.Passed);
        var requiredIds = DistinctInOrder(
            groundedInput.Sections
                .OrderBy(section => section.Order)
                .SelectMany(section => section.SourceItemIds));
        var requiredSet = requiredIds.ToHashSet(StringComparer.Ordinal);
        var coveredSet = projected
            .Where(item => item.IsResolved && requiredSet.Contains(item.SourceItemId))
            .Select(item => item.SourceItemId)
            .ToHashSet(StringComparer.Ordinal);
        var coveredIds = requiredIds.Where(coveredSet.Contains).ToArray();
        var omittedIds = requiredIds.Where(id => !coveredSet.Contains(id)).ToArray();
        var unexpectedIds = DistinctInOrder(
            projected
                .Where(item => !item.IsResolved)
                .Select(item => item.SourceItemId));

        var projectedLookup = BuildLookup(
            projected.Where(item => item.IsResolved),
            item => item.SourceItemId);
        var findingLookup = BuildLookup(
            groundedInput.Findings,
            finding => finding.SourceItemId);
        var limitationLookup = BuildLookup(
            groundedInput.Limitations,
            limitation => limitation.SourceItemId);

        var audits = new List<StoryItemAudit>();
        foreach (var sourceItemId in requiredIds)
        {
            projectedLookup.TryGetValue(sourceItemId, out var source);
            findingLookup.TryGetValue(sourceItemId, out var finding);
            limitationLookup.TryGetValue(sourceItemId, out var limitation);
            var isCovered = source is not null;
            var isLimitation = limitation is not null;
            StoryEvidenceTrace? trace = finding is null
                ? null
                : new StoryEvidenceTrace(finding.InsightId, finding.Evidence);
            var itemReasons = new List<string>();
            if (!isCovered)
            {
                itemReasons.Add("The required grounded source item is omitted.");
            }
            if (isCovered && finding is not null && !trace!.HasResolvedEvidence)
            {
                itemReasons.Add("The analytical finding has no resolved grounded evidence.");
            }
            if (source is not null && finding is not null)
            {
                itemReasons.AddRange(StorySemanticSafetyAuditor.Audit(
                    new GeneratedStoryItem(source.SourceItemId, source.GeneratedText),
                    finding,
                    groundedInput));
            }

            audits.Add(new StoryItemAudit(
                sourceItemId,
                finding?.InsightId ?? limitation?.InsightId,
                finding?.Role ?? (isLimitation ? "MISSING_CONTEXT" : null),
                isLimitation,
                isCovered,
                trace?.HasResolvedEvidence ?? false,
                isLimitation
                    ? StoryEvidenceStrength.NotApplicable
                    : trace?.HasResolvedEvidence == true
                        ? StoryEvidenceStrength.Strong
                        : StoryEvidenceStrength.None,
                trace,
                itemReasons));
        }

        foreach (var unexpected in projected.Where(item => !item.IsResolved))
        {
            if (audits.Any(item => string.Equals(
                item.SourceItemId,
                unexpected.SourceItemId,
                StringComparison.Ordinal)))
            {
                continue;
            }

            audits.Add(new StoryItemAudit(
                unexpected.SourceItemId,
                null,
                null,
                false,
                false,
                false,
                StoryEvidenceStrength.None,
                null,
                ["The generated source item is not present in the grounded input."]));
        }

        var evidenceCandidates = DistinctInOrder(
                projected
                    .Where(item => item.IsResolved && !item.IsLimitation)
                    .Select(item => item.SourceItemId))
            .Select(id => projectedLookup[id])
            .ToArray();
        var evidenceCovered = evidenceCandidates.Count(
            item => item.ResolvedEvidence.Count > 0);
        var storyCoverageScore = Score(coveredIds.Length, requiredIds.Count);
        var evidenceCoverageScore = Score(
            evidenceCovered,
            evidenceCandidates.Length);

        var reasons = new List<string>();
        if (omittedIds.Length > 0)
        {
            reasons.Add("One or more required grounded source items are omitted.");
        }
        if (unexpectedIds.Count > 0)
        {
            reasons.Add("One or more generated source items are unexpected.");
        }
        if (evidenceCovered < evidenceCandidates.Length)
        {
            reasons.Add("One or more generated analytical findings lack resolved grounded evidence.");
        }
        if (hasNumericalMismatch)
        {
            reasons.Add("Generated story contains unsupported numerical values.");
        }
        if (audits.Any(audit => audit.Reasons.Any(reason => reason.StartsWith(
                StoryDataDiffResult.SemanticSafetyReasonPrefix,
                StringComparison.Ordinal))))
        {
            reasons.Add("Generated story contains a material semantic safety violation.");
        }

        return new StoryDataDiffResult(
            reasons.Count == 0 ? StoryDataDiffStatus.Pass : StoryDataDiffStatus.Fail,
            storyCoverageScore,
            evidenceCoverageScore,
            requiredIds,
            coveredIds,
            omittedIds,
            unexpectedIds,
            audits,
            numericalAudits,
            reasons,
            [SemanticAuditLimitation]);
    }

    private static IReadOnlyList<string> DistinctInOrder(IEnumerable<string> ids)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        return ids.Where(seen.Add).ToArray();
    }

    private static IReadOnlyDictionary<string, T> BuildLookup<T>(
        IEnumerable<T> items,
        Func<T, string> idSelector)
    {
        var result = new Dictionary<string, T>(StringComparer.Ordinal);
        foreach (var item in items)
        {
            result.TryAdd(idSelector(item), item);
        }
        return result;
    }

    private static double Score(int covered, int total) =>
        total == 0 ? 1.0 : Math.Clamp((double)covered / total, 0.0, 1.0);
}
