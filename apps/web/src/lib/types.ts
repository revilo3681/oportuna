export type CategoryRef = { key: string; label: string };
export type TagRef = { key: string; label: string };

export type ConfidenceReason = {
  code: string;
  label: string;
  impact: "positive" | "negative" | "neutral";
  weight: number;
};

export type Deadline = {
  registration_deadline: string | null;
  submission_deadline: string | null;
  effective: string | null;
  kind: "registration" | "submission" | null;
  label: string;
  urgency: "expired" | "imminent" | "soon" | "upcoming" | "distant" | "unknown";
  is_open: boolean;
};

export type Verification = {
  state: "verified" | "pending" | "conflict" | "closed";
  label: string;
  confidence: number;
  confidence_pct: number;
  reasons: ConfidenceReason[];
  conflict_count: number;
  review_state: "published" | "needs_review" | "approved" | "hidden";
  review_label: string;
  review_reason: string | null;
  published: boolean;
  last_checked_at: string | null;
  last_verified_at: string | null;
  is_demo: boolean;
};

export type SourceRef = {
  name: string;
  slug: string;
  authority: number;
  url: string;
  retrieved_at: string | null;
};

export type OpportunityCard = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: CategoryRef;
  subcategory: string | null;
  tech_tags: TagRef[];
  modality: { key: string; label: string };
  country: { code: string; name: string | null } | null;
  city: string | null;
  language: string | null;
  organizer: string | null;
  official_url: string;
  registration_url: string | null;
  event_start: string | null;
  event_end: string | null;
  event_range: string;
  deadline: Deadline;
  lifecycle: { key: string; label: string };
  registration_state: string;
  verification: Verification;
  source: SourceRef | null;
  cost: { type: string; label: string; amount: number | null; currency: string | null };
  prizes_summary: string | null;
  duration_minutes: number | null;
  prep_time_minutes: number | null;
  commitment_minutes: number | null;
  duration_known: boolean;
  eligibility: Record<string, unknown>;
  eligibility_summary: string[];
  team_min: number | null;
  team_max: number | null;
  quality_score: number;
  reasons: { kind: string; label: string }[];
  first_seen_at: string | null;
  last_checked_at: string | null;
  is_demo: boolean;
  now: string;
};

export type ProvenanceRow = {
  field: string;
  value: unknown;
  observed_at: string | null;
  method: string;
  confidence: number;
  is_official: boolean;
  note: string | null;
  source: { name: string; slug: string; authority: number } | null;
};

export type OpportunityChange = {
  field: string;
  old_value: unknown;
  new_value: unknown;
  actor: string;
  reason: string | null;
  created_at: string | null;
};

export type VerificationCheck = {
  outcome: string;
  checked_at: string | null;
  http_status: number | null;
  evidence: Record<string, unknown>;
};

export type OpportunitySourceDetail = {
  name: string;
  slug: string;
  homepage_url: string;
  authority: number;
  source_url: string;
  external_id: string | null;
  retrieved_at: string | null;
  notes: string;
};

export type NextStep = { kind: string; label: string; detail: string };

export type OpportunityDetail = OpportunityCard & {
  description: string;
  registration_open_at: string | null;
  submission_deadline: string | null;
  results_at: string | null;
  phases: Record<string, unknown>[];
  timezone: string | null;
  commitment_note: string | null;
  prizes: Record<string, unknown>[];
  provenance: ProvenanceRow[];
  changes: OpportunityChange[];
  checks: VerificationCheck[];
  sources: OpportunitySourceDetail[];
  saved: { state: string; useful: boolean | null; notes: string | null } | null;
  related: OpportunityCard[];
  next_steps: NextStep[];
};

export type DashboardData = {
  personalized: boolean;
  profile_completeness: number;
  summary: {
    new: number;
    upcoming: number;
    priority: number;
    priority_label: string;
    open_total: number;
    published_total: number;
    categories: number;
    active_sources: number;
  };
  note: string;
  priority: OpportunityCard[];
  new: OpportunityCard[];
  upcoming: OpportunityCard[];
  categories: {
    key: string;
    label: string;
    tagline: string;
    count: number;
    next_deadline: string | null;
  }[];
  freshness: { last_checked_at: string | null; generated_at: string };
  weights: Record<string, number>;
};

export type Facet = { key: string; label?: string; count: number };
export type Facets = {
  category: Facet[];
  tech: Facet[];
  modality: Facet[];
  cost: Facet[];
  country: Facet[];
  language: Facet[];
};

export type CatalogResponse = {
  items: OpportunityCard[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  facets: Facets;
  applied: {
    q: string;
    category: string[];
    tech: string[];
    modality: string | null;
    country: string | null;
    language: string | null;
    cost: string | null;
    days: number | null;
    include_closed: boolean;
    sort: string;
  };
};

export type Profile = {
  interests: string[];
  level: string | null;
  goals: string[];
  country: string | null;
  city: string | null;
  travel_radius_km: number | null;
  modalities: string[];
  languages: string[];
  availability: { days?: string[]; slots?: string[] };
  time_preferences: string[];
  budget: string | null;
  eligibility: { age?: number | null; is_student?: boolean | null; [key: string]: unknown };
  preferences: Record<string, unknown>;
  onboarded_at: string | null;
  completeness: number;
};

export type SessionUser = {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
  created_at: string | null;
  profile: Profile;
};

export type Taxonomy = {
  categories: { key: string; label: string; tagline: string; description: string; subcategories: string[] }[];
  tech: { key: string; label: string }[];
  modalities: Record<string, string>;
  costs: Record<string, string>;
  lifecycles: Record<string, string>;
  verification_states: Record<string, string>;
  levels: Record<string, string>;
  goals: Record<string, string>;
  time_buckets: Record<string, string>;
  budgets: Record<string, string>;
  languages: Record<string, string>;
  regions: Record<string, string>;
  countries: { code: string; name: string | null }[];
  countries_all: { code: string; name: string | null }[];
};

export type PublicSource = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  homepage_url: string;
  endpoint: string;
  region: string;
  languages: string[];
  authority: number;
  enabled: boolean;
  frequency_minutes: number;
  last_run_at: string | null;
  last_status: string | null;
  last_error: string | null;
  consecutive_failures: number;
  disabled_reason: string | null;
  access_notes: string;
  terms_url: string | null;
  published_count: number;
};

export type Methodology = {
  totals: { published: number; verified: number; pending_review: number; sources: number };
  weights: Record<string, number>;
  verification_states: Record<string, string>;
  publication_policy: {
    summary: string;
    min_confidence: number;
    max_age_days: number;
    gates: string[];
  };
  confidence_signals: string[];
  trust_rules: string[];
  update_policy: string[];
};

export type AdminStats = {
  totals: {
    opportunities: number;
    published: number;
    review_queue: number;
    conflicts: number;
    stale_published: number;
    open_duplicates: number;
    sources: number;
    sources_enabled: number;
    sources_failing: number;
    avg_confidence: number;
    freshness_hours: number | null;
    last_checked_at: string | null;
  };
  ingestion_24h: {
    found: number;
    created: number;
    updated: number;
    published: number;
    review: number;
    errors: number;
    cost_usd: number;
    runs: number;
  };
  coverage: {
    category: Facet[];
    country: Facet[];
    language: Facet[];
    region: Facet[];
  };
  recent_runs: {
    id: string;
    source: string;
    status: string;
    started_at: string | null;
    finished_at: string | null;
    items_found: number;
    items_created: number;
    items_updated: number;
    items_published: number;
    items_review: number;
    errors: number;
    duration_ms: number | null;
    cost_usd: number;
    error_detail: string | null;
  }[];
};

export type AdminSource = PublicSource & { config: Record<string, unknown> };

export type DuplicatePair = {
  id: string;
  score: number;
  reasons: { code: string; label: string; value: number }[];
  status: string;
  created_at: string | null;
  left: DuplicateSide;
  right: DuplicateSide;
};
type DuplicateSide = {
  id: string;
  slug: string;
  title: string;
  published: boolean;
  event_start: string | null;
  organizer: string | null;
  official_url: string;
  source_count: number;
};

export type AssistantAnswer = {
  answer: string;
  items: OpportunityCard[];
  filters: Record<string, unknown>;
  citations: {
    slug: string;
    title: string;
    official_url: string;
    source: string | null;
    path: string;
  }[];
  grounding: {
    mode: string;
    uses_llm: boolean;
    published_only: boolean;
    note: string;
    model?: string | null;
    embed_model?: string | null;
    latency_ms?: number;
    retrieved?: number;
    semantic_search?: boolean;
    error?: string | null;
  };
  ai?: AssistantStatus;
};

export type AssistantStatus = {
  available: boolean;
  enabled: boolean;
  provider: string;
  model: string | null;
  embed_model: string | null;
  models: string[];
  base_url?: string;
  detail: string | null;
};

export type CalendarItem = {
  uid: string;
  slug: string;
  title: string;
  date: string;
  end?: string | null;
  kind: "deadline" | "event";
  label: string;
  url: string;
  tracking: string;
};

export type CalendarResponse = {
  items: CalendarItem[];
  range: { start: string; end: string };
};
