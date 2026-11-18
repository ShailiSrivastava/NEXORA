
"use client";

import { FormEvent, type ReactNode, useState } from "react";
import { Sidebar, MobileNav } from "@/components/sidebar";
import {
  getRecommendations,
  runEvaluation,
  saveProfile,
} from "@/lib/api";
import type {
  CandidateProfile,
  EvaluationResponse,
  JobItem,
  ViewId,
} from "@/lib/types";

const initialProfile: CandidateProfile = {
  skills: [],
  experience_level: "",
  location: "",
  preferences: { remote: false },
  preferred_role: "",
};

function Header({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <header className="mb-7">
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-violet-400">
        Nexora Intelligence
      </p>
      <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
    </header>
  );
}

function Badge({
  children,
  green,
}: {
  children: ReactNode;
  green?: boolean;
}) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs ${
        green
          ? "border-emerald-400/20 bg-emerald-400/8 text-emerald-300"
          : "border-violet-400/20 bg-violet-400/8 text-violet-300"
      }`}
    >
      {children}
    </span>
  );
}

function Empty({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-12 text-center">
      <div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-xl bg-violet-500/10 text-violet-300">
        +
      </div>
      <h3 className="font-medium text-slate-200">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        {detail}
      </p>
    </div>
  );
}

function JobCard({
  job,
  skills,
}: {
  job: JobItem;
  skills: string[];
}) {
  const raw = job.final_score ?? job.rerank_score ?? job.score;

  const percent =
    typeof raw === "number"
      ? Math.max(0, Math.min(99, Math.round(raw * 100)))
      : null;

  return (
    <article className="rounded-2xl border border-white/7 bg-[#11162b] p-5 transition hover:border-violet-400/25">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-white">{job.title}</h3>
          <p className="mt-1 text-sm text-slate-400">{job.company}</p>
        </div>

        {percent !== null && (
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full border-4 border-violet-400/60 text-sm font-semibold text-white">
            {percent}%
          </div>
        )}
      </div>

      <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-400">
        {job.description}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {job.location && <Badge>{job.location}</Badge>}
        {job.remote && <Badge green>Remote</Badge>}
        {job.experience_level && <Badge>{job.experience_level}</Badge>}
      </div>

      {job.required_skills?.length > 0 && (
        <div className="mt-4 border-t border-white/6 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-slate-500">
            Required skills
          </p>

          <div className="flex flex-wrap gap-2">
            {job.required_skills.slice(0, 6).map((skill) => {
              const matched = skills.some(
                (item) => item.toLowerCase() === skill.toLowerCase()
              );

              return (
                <span
                  key={skill}
                  className={`rounded-md px-2 py-1 text-xs ${
                    matched
                      ? "bg-violet-500/12 text-violet-200"
                      : "bg-white/5 text-slate-400"
                  }`}
                >
                  {skill}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {job.explanation && (
        <p className="mt-4 text-xs leading-5 text-slate-500">
          {job.explanation}
        </p>
      )}
    </article>
  );
}

export default function Dashboard() {
  const [active, setActive] = useState<ViewId>("overview");

  const [sessionId] = useState("nexora-session-01");

  const [profile, setProfile] =
    useState<CandidateProfile>(initialProfile);

  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");

  const [query, setQuery] = useState("");
  const [recommendations, setRecommendations] = useState<JobItem[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsError, setJobsError] = useState("");

  const [evaluation, setEvaluation] =
    useState<EvaluationResponse | null>(null);

  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [evaluationError, setEvaluationError] = useState("");

  const profileComplete = Boolean(
    profile.skills.length ||
      profile.experience_level ||
      profile.location ||
      profile.preferred_role
  );

  async function handleSaveProfile(event: FormEvent) {
    event.preventDefault();

    setProfileSaving(true);
    setProfileMessage("");

    try {
      await saveProfile(sessionId, profile);
      setProfileMessage("Profile saved successfully.");
    } catch (error) {
      setProfileMessage(
        error instanceof Error
          ? error.message
          : "Could not save the profile."
      );
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault();

    if (!query.trim()) return;

    setJobsLoading(true);
    setJobsError("");
    setRecommendations([]);

    try {
      const result = await getRecommendations(
        sessionId,
        query.trim(),
        5
      );

      setRecommendations(result.final_personalized_ranking);
    } catch (error) {
      setJobsError(
        error instanceof Error
          ? error.message
          : "Could not retrieve job recommendations."
      );
    } finally {
      setJobsLoading(false);
    }
  }

  async function handleEvaluation() {
    setEvaluationLoading(true);
    setEvaluationError("");

    try {
      setEvaluation(await runEvaluation(5, false));
    } catch (error) {
      setEvaluationError(
        error instanceof Error
          ? error.message
          : "The evaluation could not be executed."
      );
    } finally {
      setEvaluationLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#080b1b] text-slate-200 lg:flex">
      <Sidebar active={active} onChange={setActive} />

      <main className="min-w-0 flex-1 px-4 pb-24 pt-5 sm:px-7 lg:px-10 lg:pb-10 lg:pt-8">
        <div className="mx-auto max-w-7xl">

          {/* OVERVIEW */}
          {active === "overview" && (
            <section>
              <Header
                title="Career intelligence dashboard"
                subtitle="Track your career readiness and discover opportunities matched to your skills."
              />

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  {
                    label: "Profile status",
                    value: profileComplete ? "Ready" : "Incomplete",
                  },
                  {
                    label: "Total skills",
                    value: profile.skills.length,
                  },
                  {
                    label: "Recommended jobs",
                    value: recommendations.length,
                  },
                  {
                    label: "Evaluation",
                    value: evaluation ? "Completed" : "Not run",
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-2xl border border-white/7 bg-[#11162b] p-5"
                  >
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
                      {item.label}
                    </p>
                    <p className="mt-3 text-2xl font-semibold text-white">
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
                <div className="rounded-2xl border border-white/7 bg-[#11162b] p-5 sm:p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <h2 className="font-semibold text-white">
                      Recommended opportunities
                    </h2>

                    <button
                      onClick={() => setActive("jobs")}
                      className="text-xs text-violet-300"
                    >
                      Discover more
                    </button>
                  </div>

                  {recommendations.length ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      {recommendations.slice(0, 4).map((job) => (
                        <JobCard
                          key={job.job_id}
                          job={job}
                          skills={profile.skills}
                        />
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="No recommendations loaded"
                      detail="Search for roles in Discover Jobs to retrieve personalized job rankings."
                    />
                  )}
                </div>

                <div className="rounded-2xl border border-white/7 bg-[#11162b] p-5">
                  <h2 className="font-semibold text-white">
                    Candidate profile
                  </h2>

                  {profileComplete ? (
                    <div className="mt-5 space-y-4">
                      <div>
                        <p className="text-xs text-slate-500">
                          Preferred role
                        </p>
                        <p className="mt-1 text-sm text-white">
                          {profile.preferred_role || "Not set"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">
                          Experience
                        </p>
                        <p className="mt-1 text-sm text-white">
                          {profile.experience_level || "Not set"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">
                          Location
                        </p>
                        <p className="mt-1 text-sm text-white">
                          {profile.location || "Not set"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">Skills</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {profile.skills.map((skill) => (
                            <span
                              key={skill}
                              className="rounded-md bg-violet-500/10 px-2 py-1 text-xs text-violet-200"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-5 text-sm leading-6 text-slate-500">
                      Complete your candidate profile to improve personalized job rankings.
                    </p>
                  )}

                  <button
                    onClick={() => setActive("profile")}
                    className="mt-5 w-full rounded-xl border border-white/8 py-2.5 text-sm text-slate-300 hover:bg-white/4"
                  >
                    Edit profile
                  </button>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-white/7 bg-[#11162b] p-6">
                <h2 className="font-semibold text-white">
                  Your career journey
                </h2>

                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Build your professional profile, discover suitable opportunities,
                  compare job requirements with your skills, and evaluate retrieval performance.
                </p>

                <button
                  onClick={() => setActive("jobs")}
                  className="mt-5 rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium text-white hover:bg-violet-400"
                >
                  Explore opportunities
                </button>
              </div>
            </section>
          )}

          {/* JOB DISCOVERY */}
          {active === "jobs" && (
            <section>
              <Header
                title="Discover jobs"
                subtitle="Search the indexed job database and receive personalized rankings."
              />

              <form
                onSubmit={handleSearch}
                className="mb-6 flex gap-3"
              >
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Try: Python backend engineer Bengaluru"
                  className="min-w-0 flex-1 rounded-xl border border-white/8 bg-[#11162b] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-violet-400/50"
                />

                <button
                  disabled={jobsLoading}
                  className="rounded-xl bg-violet-500 px-5 text-sm font-medium text-white hover:bg-violet-400 disabled:opacity-50"
                >
                  {jobsLoading ? "Searching..." : "Search"}
                </button>
              </form>

              {jobsError && (
                <div className="mb-5 rounded-xl border border-red-400/20 bg-red-400/8 px-4 py-3 text-sm text-red-300">
                  {jobsError}
                </div>
              )}

              {jobsLoading ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {[1, 2, 3].map((item) => (
                    <div
                      key={item}
                      className="h-64 animate-pulse rounded-2xl border border-white/6 bg-white/[0.025]"
                    />
                  ))}
                </div>
              ) : recommendations.length ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {recommendations.map((job) => (
                    <JobCard
                      key={job.job_id}
                      job={job}
                      skills={profile.skills}
                    />
                  ))}
                </div>
              ) : (
                <Empty
                  title="Search for a role"
                  detail="Enter a job title or skill to retrieve matching jobs from the backend."
                />
              )}
            </section>
          )}

          {/* CANDIDATE PROFILE */}
          {active === "profile" && (
            <section>
              <Header
                title="Candidate profile"
                subtitle="Manage the skills and preferences used for personalized job matching."
              />

              <form
                onSubmit={handleSaveProfile}
                className="max-w-3xl rounded-2xl border border-white/7 bg-[#11162b] p-5 sm:p-7"
              >
                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="sm:col-span-2">
                    <span className="mb-2 block text-xs text-slate-400">
                      Skills — comma separated
                    </span>

                    <input
                      value={profile.skills.join(", ")}
                      onChange={(event) =>
                        setProfile({
                          ...profile,
                          skills: event.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean),
                        })
                      }
                      placeholder="Java, Python, React, FastAPI"
                      className="w-full rounded-xl border border-white/8 bg-[#080b1b] px-4 py-3 text-sm outline-none focus:border-violet-400/50"
                    />
                  </label>

                  <label>
                    <span className="mb-2 block text-xs text-slate-400">
                      Experience level
                    </span>

                    <select
                      value={profile.experience_level}
                      onChange={(event) =>
                        setProfile({
                          ...profile,
                          experience_level: event.target.value,
                        })
                      }
                      className="w-full rounded-xl border border-white/8 bg-[#080b1b] px-4 py-3 text-sm outline-none"
                    >
                      <option value="">Select level</option>
                      <option value="junior">Junior</option>
                      <option value="mid">Mid-level</option>
                      <option value="senior">Senior</option>
                      <option value="lead">Lead</option>
                    </select>
                  </label>

                  <label>
                    <span className="mb-2 block text-xs text-slate-400">
                      Preferred location
                    </span>

                    <input
                      value={profile.location}
                      onChange={(event) =>
                        setProfile({
                          ...profile,
                          location: event.target.value,
                        })
                      }
                      placeholder="Bengaluru or Remote"
                      className="w-full rounded-xl border border-white/8 bg-[#080b1b] px-4 py-3 text-sm outline-none"
                    />
                  </label>

                  <label>
                    <span className="mb-2 block text-xs text-slate-400">
                      Desired role
                    </span>

                    <input
                      value={profile.preferred_role}
                      onChange={(event) =>
                        setProfile({
                          ...profile,
                          preferred_role: event.target.value,
                        })
                      }
                      placeholder="Software Development Engineer"
                      className="w-full rounded-xl border border-white/8 bg-[#080b1b] px-4 py-3 text-sm outline-none"
                    />
                  </label>

                  <label className="flex items-end pb-3">
                    <span className="flex items-center gap-3 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        checked={profile.preferences.remote}
                        onChange={(event) =>
                          setProfile({
                            ...profile,
                            preferences: {
                              remote: event.target.checked,
                            },
                          })
                        }
                        className="h-4 w-4 accent-violet-500"
                      />
                      Open to remote work
                    </span>
                  </label>
                </div>

                <div className="mt-6 flex items-center gap-4">
                  <button
                    disabled={profileSaving}
                    className="rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                  >
                    {profileSaving ? "Saving..." : "Save profile"}
                  </button>

                  {profileMessage && (
                    <p className="text-sm text-slate-400">
                      {profileMessage}
                    </p>
                  )}
                </div>
              </form>
            </section>
          )}

          {/* EVALUATION ANALYTICS */}
          {active === "evaluation" && (
            <section>
              <Header
                title="Evaluation analytics"
                subtitle="Measure the quality of job retrieval and personalized ranking."
              />

              <div className="mb-6 flex items-center gap-3">
                <button
                  onClick={handleEvaluation}
                  disabled={evaluationLoading}
                  className="rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                >
                  {evaluationLoading
                    ? "Running evaluation..."
                    : "Run evaluation"}
                </button>

                <span className="text-xs text-slate-500">
                  Top 5 results · 30 ground-truth queries
                </span>
              </div>

              {evaluationError && (
                <div className="mb-5 rounded-xl border border-red-400/20 bg-red-400/8 px-4 py-3 text-sm text-red-300">
                  {evaluationError}
                </div>
              )}

              {evaluationLoading && (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {[1, 2, 3, 4].map((item) => (
                    <div
                      key={item}
                      className="h-28 animate-pulse rounded-2xl border border-white/6 bg-white/[0.025]"
                    />
                  ))}
                </div>
              )}

              {!evaluationLoading && evaluation && (
                <div>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {(
                      [
                        ["precision@5", "Precision@5"],
                        ["recall@5", "Recall@5"],
                        ["mrr", "MRR"],
                        ["ndcg@5", "NDCG@5"],
                      ] as const
                    ).map(([key, label]) => (
                      <div
                        key={key}
                        className="rounded-2xl border border-white/7 bg-[#11162b] p-5"
                      >
                        <p className="text-xs uppercase tracking-[0.14em] text-slate-500">
                          {label}
                        </p>

                        <p className="mt-3 text-2xl font-semibold text-white">
                          {evaluation.summary.personalized[key].toFixed(4)}
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                          Personalized result
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 overflow-x-auto rounded-2xl border border-white/7 bg-[#11162b]">
                    <table className="w-full min-w-[620px] text-left text-sm">
                      <thead>
                        <tr className="border-b border-white/7 text-xs uppercase tracking-[0.12em] text-slate-500">
                          <th className="px-5 py-4">Strategy</th>
                          <th className="px-5 py-4">Precision@5</th>
                          <th className="px-5 py-4">Recall@5</th>
                          <th className="px-5 py-4">MRR</th>
                          <th className="px-5 py-4">NDCG@5</th>
                        </tr>
                      </thead>

                      <tbody>
                        {(
                          ["baseline", "reranked", "personalized"] as const
                        ).map((strategy) => (
                          <tr
                            key={strategy}
                            className="border-b border-white/5 last:border-0"
                          >
                            <td className="px-5 py-4 capitalize text-slate-300">
                              {strategy}
                            </td>
                            <td className="px-5 py-4 text-white">
                              {evaluation.summary[strategy]["precision@5"].toFixed(4)}
                            </td>
                            <td className="px-5 py-4 text-white">
                              {evaluation.summary[strategy]["recall@5"].toFixed(4)}
                            </td>
                            <td className="px-5 py-4 text-white">
                              {evaluation.summary[strategy].mrr.toFixed(4)}
                            </td>
                            <td className="px-5 py-4 text-white">
                              {evaluation.summary[strategy]["ndcg@5"].toFixed(4)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {evaluation.ragas && (
                    <div className="mt-5 rounded-2xl border border-white/7 bg-[#11162b] p-5">
                      <p className="text-sm text-slate-300">
                        Ragas: {evaluation.ragas.status}
                      </p>

                      {evaluation.ragas.reason && (
                        <p className="mt-2 text-sm text-slate-500">
                          {evaluation.ragas.reason}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {!evaluationLoading &&
                !evaluation &&
                !evaluationError && (
                  <Empty
                    title="Evaluation not yet run"
                    detail="Run the evaluation to calculate retrieval and ranking metrics from the backend."
                  />
                )}
            </section>
          )}

        </div>
      </main>

      <MobileNav active={active} onChange={setActive} />
    </div>
  );
}
