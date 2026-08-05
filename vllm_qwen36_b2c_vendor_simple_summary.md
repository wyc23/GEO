# vLLM Qwen3.6 Dataset Diagnostics Summary

- Completed valid records: 121
- Skipped invalid records: 38
- Failed method answers: 38
- Failed metric entries: 114

## Mean Target Improvement

| Method | Metric | N | Mean | Positive Rate |
|---|---|---:|---:|---:|
| `identity` | `simple_wordpos` | 115 | -0.000284 | 0.365 |
| `identity` | `simple_word` | 115 | -0.000601 | 0.357 |
| `identity` | `simple_pos` | 115 | -0.005855 | 0.330 |
| `fluent_gpt` | `simple_wordpos` | 112 | 0.013063 | 0.402 |
| `fluent_gpt` | `simple_word` | 112 | 0.011183 | 0.420 |
| `fluent_gpt` | `simple_pos` | 112 | 0.011730 | 0.411 |
| `unique_words_gpt` | `simple_wordpos` | 113 | 0.000691 | 0.407 |
| `unique_words_gpt` | `simple_word` | 113 | 0.002190 | 0.389 |
| `unique_words_gpt` | `simple_pos` | 113 | 0.000932 | 0.372 |
| `authoritative_mine` | `simple_wordpos` | 113 | 0.003263 | 0.416 |
| `authoritative_mine` | `simple_word` | 113 | 0.004056 | 0.425 |
| `authoritative_mine` | `simple_pos` | 113 | 0.002577 | 0.398 |
| `more_quotes_mine` | `simple_wordpos` | 114 | -0.006064 | 0.342 |
| `more_quotes_mine` | `simple_word` | 114 | -0.007640 | 0.342 |
| `more_quotes_mine` | `simple_pos` | 114 | -0.007513 | 0.333 |
| `citing_credible_mine` | `simple_wordpos` | 115 | 0.000710 | 0.391 |
| `citing_credible_mine` | `simple_word` | 115 | -0.001341 | 0.391 |
| `citing_credible_mine` | `simple_pos` | 115 | -0.002910 | 0.365 |
| `simple_language_mine` | `simple_wordpos` | 112 | -0.003307 | 0.339 |
| `simple_language_mine` | `simple_word` | 112 | -0.001157 | 0.357 |
| `simple_language_mine` | `simple_pos` | 112 | -0.001732 | 0.366 |
| `technical_terms_mine` | `simple_wordpos` | 116 | -0.006045 | 0.397 |
| `technical_terms_mine` | `simple_word` | 116 | -0.005379 | 0.328 |
| `technical_terms_mine` | `simple_pos` | 116 | -0.005675 | 0.379 |
| `stats_optimization_gpt` | `simple_wordpos` | 112 | 0.013337 | 0.446 |
| `stats_optimization_gpt` | `simple_word` | 112 | 0.011924 | 0.429 |
| `stats_optimization_gpt` | `simple_pos` | 112 | 0.012962 | 0.473 |
| `seo_optimize_mine2` | `simple_wordpos` | 113 | -0.004841 | 0.363 |
| `seo_optimize_mine2` | `simple_word` | 113 | -0.005212 | 0.372 |
| `seo_optimize_mine2` | `simple_pos` | 113 | -0.006069 | 0.363 |

## Failed Method Answers

| Line | Method | Error |
|---:|---|---|
| 4 | `authoritative_mine` | `missing_or_invalid_citations` |
| 6 | `citing_credible_mine` | `missing_or_invalid_citations` |
| 9 | `fluent_gpt` | `missing_or_invalid_citations` |
| 9 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 9 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 17 | `authoritative_mine` | `missing_or_invalid_citations` |
| 18 | `fluent_gpt` | `missing_or_invalid_citations` |
| 18 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 18 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 22 | `authoritative_mine` | `missing_or_invalid_citations` |
| 35 | `simple_language_mine` | `missing_or_invalid_citations` |
| 39 | `authoritative_mine` | `missing_or_invalid_citations` |
| 39 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 42 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 43 | `identity` | `missing_or_invalid_citations` |
| 46 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 52 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 58 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 58 | `simple_language_mine` | `missing_or_invalid_citations` |
| 58 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 62 | `simple_language_mine` | `missing_or_invalid_citations` |
| 69 | `fluent_gpt` | `missing_or_invalid_citations` |
| 69 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 69 | `citing_credible_mine` | `missing_or_invalid_citations` |
| 78 | `simple_language_mine` | `missing_or_invalid_citations` |
| 86 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 86 | `simple_language_mine` | `missing_or_invalid_citations` |
| 87 | `technical_terms_mine` | `missing_or_invalid_citations` |
| 87 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 87 | `seo_optimize_mine2` | `missing_or_invalid_citations` |
| 101 | `fluent_gpt` | `missing_or_invalid_citations` |
| 109 | `simple_language_mine` | `missing_or_invalid_citations` |
| 119 | `more_quotes_mine` | `missing_or_invalid_citations` |
| 120 | `fluent_gpt` | `missing_or_invalid_citations` |
| 120 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 129 | `stats_optimization_gpt` | `missing_or_invalid_citations` |
| 145 | `unique_words_gpt` | `missing_or_invalid_citations` |
| 156 | `identity` | `missing_or_invalid_citations` |
