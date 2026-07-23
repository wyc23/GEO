# vLLM Qwen3.6 Dataset Diagnostics Summary

- Completed valid records: 100
- Skipped invalid records: 60
- Failed method answers: 47
- Failed metric entries: 141

## Mean Target Improvement

| Method | Metric | N | Mean | Positive Rate |
|---|---|---:|---:|---:|
| `identity` | `simple_wordpos` | 92 | 0.009827 | 0.424 |
| `identity` | `simple_word` | 92 | 0.011603 | 0.424 |
| `identity` | `simple_pos` | 92 | 0.008751 | 0.424 |
| `fluent_gpt` | `simple_wordpos` | 89 | 0.011276 | 0.461 |
| `fluent_gpt` | `simple_word` | 89 | 0.017593 | 0.483 |
| `fluent_gpt` | `simple_pos` | 89 | 0.007978 | 0.461 |
| `unique_words_gpt` | `simple_wordpos` | 90 | 0.004690 | 0.411 |
| `unique_words_gpt` | `simple_word` | 90 | 0.008011 | 0.467 |
| `unique_words_gpt` | `simple_pos` | 90 | 0.006554 | 0.433 |
| `authoritative_mine` | `simple_wordpos` | 90 | -0.015596 | 0.389 |
| `authoritative_mine` | `simple_word` | 90 | -0.012437 | 0.400 |
| `authoritative_mine` | `simple_pos` | 90 | -0.012266 | 0.400 |
| `more_quotes_mine` | `simple_wordpos` | 92 | -0.000017 | 0.424 |
| `more_quotes_mine` | `simple_word` | 92 | 0.002245 | 0.435 |
| `more_quotes_mine` | `simple_pos` | 92 | 0.003988 | 0.435 |
| `citing_credible_mine` | `simple_wordpos` | 92 | -0.000778 | 0.446 |
| `citing_credible_mine` | `simple_word` | 92 | 0.004668 | 0.478 |
| `citing_credible_mine` | `simple_pos` | 92 | 0.002304 | 0.402 |
| `simple_language_mine` | `simple_wordpos` | 87 | 0.003014 | 0.448 |
| `simple_language_mine` | `simple_word` | 87 | 0.009651 | 0.460 |
| `simple_language_mine` | `simple_pos` | 87 | -0.000518 | 0.425 |
| `technical_terms_mine` | `simple_wordpos` | 93 | 0.012560 | 0.452 |
| `technical_terms_mine` | `simple_word` | 93 | 0.015910 | 0.452 |
| `technical_terms_mine` | `simple_pos` | 93 | 0.012502 | 0.495 |
| `stats_optimization_gpt` | `simple_wordpos` | 91 | 0.023394 | 0.527 |
| `stats_optimization_gpt` | `simple_word` | 91 | 0.028109 | 0.538 |
| `stats_optimization_gpt` | `simple_pos` | 91 | 0.025998 | 0.516 |
| `seo_optimize_mine2` | `simple_wordpos` | 90 | 0.016313 | 0.478 |
| `seo_optimize_mine2` | `simple_word` | 90 | 0.016264 | 0.478 |
| `seo_optimize_mine2` | `simple_pos` | 90 | 0.019218 | 0.467 |

## Failed Method Answers

| Line | Method | Error |
|---:|---|---|
| 2 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 2 | `simple_language_mine` | `missing_or_invalid_citations` |
| 2 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 2 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 16 | `fluent_gpt` | `missing_or_invalid_citations` |
| 16 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 16 | `authoritative_mine` | `missing_or_invalid_citations` |
| 19 | `technical_terms_mine` | `missing_or_invalid_citations` |
| 19 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 24 | `identity` | `missing_or_invalid_citations` |
| 25 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 32 | `simple_language_mine` | `missing_or_invalid_citations` |
| 33 | `authoritative_mine` | `missing_or_invalid_citations` |
| 48 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 48 | `simple_language_mine` | `missing_or_invalid_citations` |
| 49 | `fluent_gpt` | `missing_or_invalid_citations` |
| 53 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 53 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 65 | `simple_language_mine` | `missing_or_invalid_citations` |
| 66 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 69 | `technical_terms_mine` | `missing_or_invalid_citations` |
| 69 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 77 | `fluent_gpt` | `missing_or_invalid_citations` |
| 77 | `technical_terms_mine` | `missing_or_invalid_citations` |
| 77 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 79 | `fluent_gpt` | `missing_or_invalid_citations` |
| 79 | `simple_language_mine` | `missing_or_invalid_citations` |
| 83 | `authoritative_mine` | `missing_or_invalid_citations` |
| 83 | `simple_language_mine` | `missing_or_invalid_citations` |
| 85 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 85 | `citing_credible_mine` | `missing_or_invalid_citations` |
| 85 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 101 | `fluent_gpt` | `missing_or_invalid_citations` |
| 106 | `authoritative_mine` | `missing_or_invalid_citations` |
| 106 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 106 | `simple_language_mine` | `missing_or_invalid_citations` |
| 110 | `identity` | `missing_or_invalid_citations` |
| 113 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 113 | `simple_language_mine` | `missing_or_invalid_citations` |
| 115 | `fluent_gpt` | `missing_or_invalid_citations` |
| 126 | `authoritative_mine` | `missing_or_invalid_citations` |
| 126 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 126 | `citing_credible_mine` | `missing_or_invalid_citations` |
| 143 | `identity` | `missing_or_invalid_citations` |
| 143 | `fluent_gpt` | `missing_or_invalid_citations` |
| 147 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 149 | `citing_credible_mine` | `missing_or_invalid_citations` |
