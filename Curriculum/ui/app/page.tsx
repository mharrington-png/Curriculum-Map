"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

type Occurrence = {
  skill_id: string; course_id: string; course: string; unit_id: string;
  unit_title: string; priority: "review" | "required" | "extension";
  objective_id: string; objective: string;
  relationship: "prerequisite" | "required" | "method-dependent";
  progression: "introduce" | "reinforce" | "deepen" | "apply";
};
type Skill = {
  skill_id: string; description: string; introduction_status: string;
  first_introduced_course: string | null; inherited_note: string | null;
  courses: string[]; occurrences: Occurrence[];
};

const courses = [
  { id: "M12", label: "Math 12", title: "Intermediate Algebra", tone: "blue" },
  { id: "M21", label: "Math 21", title: "Algebra and its Functions", tone: "mint" },
  { id: "M22", label: "Math 22", title: "Geometry", tone: "gold" },
  { id: "M31", label: "Math 31", title: "Advanced Algebra", tone: "violet" },
  { id: "M32", label: "Math 32", title: "Precalculus: Trigonometry", tone: "coral" },
  { id: "M39", label: "Math 39", title: "Precalculus with Data Analysis", tone: "crimson" },
  { id: "M49", label: "Math 49", title: "Precalculus with Limits", tone: "navy" },
];
const roleLabel = { introduce: "Introduce", reinforce: "Reinforce", deepen: "Deepen", apply: "Apply" };
const requiredUnitOrder: Record<string, string[]> = {
  M21: ["M21-FUN", "M21-EXP", "M21-POL", "M21-QUAD", "M21-RAT"],
  M22: ["M22-BAS", "M22-CON", "M22-SIM", "M22-RGT", "M22-QUAD", "M22-CIR"],
  M31: ["M31-LIN", "M31-FUN", "M31-EXP", "M31-LOG", "M31-QUAD"],
  M32: ["M32-FND", "M32-TRI", "M32-IDN", "M32-INV", "M32-GRF", "M32-POL"],
  M39: ["M39-LIN", "M39-EXP", "M39-POW", "M39-POL", "M39-STA", "M39-PRO"],
  M49: ["M49-OPS", "M49-ALG", "M49-LIM", "M49-SS"],
};

export default function Home() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [objectiveId, setObjectiveId] = useState<string | null>(null);
  const [skillId, setSkillId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [courseIndex, setCourseIndex] = useState(0);
  const [showReview, setShowReview] = useState(true);
  const [showExtension, setShowExtension] = useState(true);
  const [showMethodDependent, setShowMethodDependent] = useState(true);

  useEffect(() => { fetch(`${import.meta.env.BASE_URL}data/skill_progressions.json`).then(r => r.json()).then(setSkills); }, []);
  const allOccurrences = useMemo(() => skills.flatMap(s => s.occurrences), [skills]);
  const selectedCourse = courses.find(c => c.id === courseId);
  const courseOccurrences = allOccurrences.filter(o => o.course_id === courseId);
  const objectives = useMemo(() => {
    const map = new Map<string, Occurrence>();
    courseOccurrences.forEach(o => map.set(o.objective_id, o));
    return [...map.values()].sort((a, b) => {
      if (a.priority === "required" && b.priority === "required") {
        const order = requiredUnitOrder[courseId || ""] || [];
        const unitDifference = order.indexOf(a.unit_id) - order.indexOf(b.unit_id);
        if (unitDifference) return unitDifference;
      }
      return a.objective_id.localeCompare(b.objective_id);
    });
  }, [courseOccurrences]);
  const selectedSkill = skills.find(s => s.skill_id === skillId);
  const searchResults = useMemo(() => {
    if (query.trim().length < 2) return { skills: [] as Skill[], objectives: [] as Occurrence[], units: [] as Occurrence[] };
    const needle = query.trim().toLowerCase();
    const matchingSkills = skills.filter(s => `${s.skill_id} ${s.description}`.toLowerCase().includes(needle)).slice(0, 6);
    const objectiveMap = new Map<string, Occurrence>();
    const unitMap = new Map<string, Occurrence>();
    allOccurrences.forEach(o => {
      if (`${o.objective_id} ${o.objective}`.toLowerCase().includes(needle)) objectiveMap.set(`${o.course_id}:${o.objective_id}`, o);
      if (`${o.unit_id} ${o.unit_title}`.toLowerCase().includes(needle)) unitMap.set(`${o.course_id}:${o.unit_id}`, o);
    });
    return { skills: matchingSkills, objectives: [...objectiveMap.values()].slice(0, 6), units: [...unitMap.values()].slice(0, 6) };
  }, [query, skills, allOccurrences]);
  const hasSearchResults = searchResults.skills.length + searchResults.objectives.length + searchResults.units.length > 0;

  const openCourse = (id: string) => { setCourseId(id); setObjectiveId(null); setSkillId(null); };
  const goHome = () => { setCourseId(null); setObjectiveId(null); setSkillId(null); };
  const flipCourse = (direction: number) => setCourseIndex(current => (current + direction + courses.length) % courses.length);
  const openObjective = (occurrence: Occurrence) => {
    setCourseId(occurrence.course_id); setObjectiveId(occurrence.objective_id); setSkillId(null); setQuery("");
  };

  useEffect(() => {
    if (!objectiveId || skillId) return;
    requestAnimationFrame(() => document.getElementById(`objective-${objectiveId}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }, [objectiveId, skillId, courseId]);

  return <main>
    <header className="topbar">
      <button className="brand" onClick={goHome}><span className="brandmark" aria-hidden="true"><img src={`${import.meta.env.BASE_URL}mx-shield-black.png`} alt="" /></span><span>Middlesex Mathematics<small>Curriculum Map</small></span></button>
      <nav><button onClick={goHome}>Courses</button></nav>
      <div className="searchbox">
        <span>⌕</span><input aria-label="Search skills" placeholder="Search a skill…" value={query} onChange={e => setQuery(e.target.value)} />
        {hasSearchResults && <div className="searchresults">
          {searchResults.skills.length > 0 && <section><h2>Skills</h2>{searchResults.skills.map(s => <button key={s.skill_id} onClick={() => { setSkillId(s.skill_id); setQuery(""); }}>{s.description}<small>{s.skill_id}</small></button>)}</section>}
          {searchResults.objectives.length > 0 && <section><h2>Objectives</h2>{searchResults.objectives.map(o => <button key={`${o.course_id}-${o.objective_id}`} onClick={() => openObjective(o)}>{o.objective}<small>{o.course} · {o.objective_id}</small></button>)}</section>}
          {searchResults.units.length > 0 && <section><h2>Units</h2>{searchResults.units.map(o => <button key={`${o.course_id}-${o.unit_id}`} onClick={() => openObjective(o)}>{o.unit_title}<small>{o.course} · {o.unit_id}</small></button>)}</section>}
        </div>}
      </div>
    </header>

    {!courseId && !skillId && <div className="shell landing">
      <section className="hero"><p className="eyebrow">Department curriculum</p><h1>Overview<br/><em>Choose a course.</em></h1><p>Flip through the curriculum, then open a course to explore its topical units, learning objectives, and supporting skills.</p></section>
      <section className="rolodex" aria-label="Course selector" onKeyDown={e => { if (e.key === "ArrowLeft") flipCourse(-1); if (e.key === "ArrowRight") flipCourse(1); }} tabIndex={0}>
        <button className="flip prev" onClick={() => flipCourse(-1)} aria-label="Previous course"><span>←</span><small>Previous</small></button>
        <div className="cardstack">{courses.map((c, i) => {
          let offset = i - courseIndex;
          if (offset > courses.length / 2) offset -= courses.length;
          if (offset < -courses.length / 2) offset += courses.length;
          const occ = allOccurrences.filter(o => o.course_id === c.id);
          const objectiveCount = new Set(occ.map(o => o.objective_id)).size;
          const skillCount = new Set(occ.map(o => o.skill_id)).size;
          return <article className={`rolocard ${c.tone} ${offset === 0 ? "current" : ""}`} style={{"--offset": offset} as CSSProperties} key={c.id} aria-hidden={offset !== 0}>
            <span className="coursecode">{c.label}</span><h2>{c.title}</h2><p>Explore this course by topical unit, then trace each objective to the skills students use.</p>
            <div className="cardstats"><span><b>{objectiveCount || "—"}</b> objectives</span><span><b>{skillCount || "—"}</b> skills</span></div>
            <button className="opencourse" onClick={() => openCourse(c.id)} tabIndex={offset === 0 ? 0 : -1}>Explore {c.label} <b>→</b></button>
          </article>;
        })}</div>
        <button className="flip next" onClick={() => flipCourse(1)} aria-label="Next course"><small>Next</small><span>→</span></button>
      </section>
      <div className="coursepicker" aria-label="Select a course">{courses.map((c, i) => <button className={i === courseIndex ? "active" : ""} key={c.id} onClick={() => setCourseIndex(i)} aria-label={`Show ${c.label}`}>{c.label}</button>)}</div>
      <p className="infinitehint">Keep flipping — the course sequence wraps around in either direction.</p>
    </div>}

    {courseId && selectedCourse && !skillId && <div className="shell page">
      <button className="back" onClick={goHome}>← All courses</button><div className="coursehead"><div><p className="eyebrow">{selectedCourse.label}</p><h1>{selectedCourse.title}</h1><p>{objectives.length} learning objectives · {new Set(courseOccurrences.map(o => o.skill_id)).size} supporting skills</p></div><a className="pdfDownload" href={`${import.meta.env.BASE_URL}downloads/${selectedCourse.id.toLowerCase()}-curriculum-at-a-glance.pdf`} download><span>↓</span><span>Download Curriculum<small>Course at a glance</small></span></a></div>
      <div className="coursebody"><section className="objectiveList">{["review","required","extension"].map(priority => {
        const group = objectives.filter(o => o.priority === priority); if (!group.length) return null;
        const units = [...new Map(group.map(o => [o.unit_id, { id: o.unit_id, title: o.unit_title }])).values()];
        return <div className="priorityGroup" key={priority}><div className="priorityHead"><h2 className={`priority ${priority}`}>{priority}</h2><span>{units.length} {units.length === 1 ? "unit" : "units"} · {group.length} objectives</span></div>{units.map(unit => {
          const unitObjectives = group.filter(o => o.unit_id === unit.id);
          const containsSelectedObjective = unitObjectives.some(o => o.objective_id === objectiveId);
          return <details className="unit" key={unit.id} open={containsSelectedObjective || undefined}><summary><span><small>{priority} unit</small><b>{unit.title}</b></span><span className="unitCount">{unitObjectives.length} objectives</span><span className="chevron">⌄</span></summary><div className="unitObjectives">{unitObjectives.map(o => {
            const isOpen = objectiveId === o.objective_id;
            const skillsForObjective = isOpen ? skills.filter(s => s.occurrences.some(x => x.objective_id === o.objective_id)) : [];
            return <div className="objectiveBranch" id={`objective-${o.objective_id}`} key={o.objective_id}><button className={isOpen ? "objective active" : "objective"} onClick={() => setObjectiveId(isOpen ? null : o.objective_id)} aria-expanded={isOpen}><small>{o.objective_id}</small><span>{o.objective}</span><b>{isOpen ? "−" : "+"}</b></button>{isOpen && <div className="nestedSkills"><p>Supporting skills</p>{skillsForObjective.map(s => { const occurrence=s.occurrences.find(x=>x.objective_id===o.objective_id)!; return <button className="skillrow" key={s.skill_id} onClick={()=>setSkillId(s.skill_id)}><span className={`dot ${occurrence.progression}`}>{roleLabel[occurrence.progression][0]}</span><span>{s.description}<small>{roleLabel[occurrence.progression]}</small></span><b>→</b></button>})}</div>}</div>;
          })}</div></details>;
        })}</div>;
      })}</section></div>
    </div>}

    {selectedSkill && <div className="shell page"><button className="back" onClick={() => setSkillId(null)}>← {selectedCourse ? selectedCourse.label : "Back"}</button><p className="eyebrow">Skill explorer</p><code>{selectedSkill.skill_id}</code><h1 className="skilltitle">{selectedSkill.description}</h1><p className="lede">{selectedSkill.introduction_status === "inherited" ? selectedSkill.inherited_note : `First introduced in ${selectedSkill.first_introduced_course}.`} Once established, this skill remains available in the student toolkit.</p>
      <fieldset className="timelineFilters"><legend>Show timeline occurrences</legend><label><input type="checkbox" checked={showReview} onChange={e => setShowReview(e.target.checked)} /> Review</label><label><input type="checkbox" checked={showExtension} onChange={e => setShowExtension(e.target.checked)} /> Extension</label><label><input type="checkbox" checked={showMethodDependent} onChange={e => setShowMethodDependent(e.target.checked)} /> Method-dependent</label></fieldset>
      <div className="timeline">{courses.map(c => { const allItems=selectedSkill.occurrences.filter(o=>o.course_id===c.id); const items=allItems.filter(o => (showReview || o.priority !== "review") && (showExtension || o.priority !== "extension") && (showMethodDependent || o.relationship !== "method-dependent")); const origin=selectedSkill.first_introduced_course; const originIndex=courses.findIndex(x=>x.label===origin); const currentIndex=courses.findIndex(x=>x.id===c.id); const carried=!allItems.length && (selectedSkill.introduction_status==="inherited" || (originIndex>=0 && currentIndex>originIndex)); return <div className={`timecourse ${allItems.length?"explicit":carried?"carried":"future"}`} key={c.id}><div className="timehead"><b>{c.label}</b>{carried&&<span>Carried forward</span>}{allItems.length > 0 && items.length === 0 && <span>Hidden by filters</span>}</div>{items.map((o,i)=><button key={`${o.objective_id}-${i}`} onClick={()=>openObjective(o)}><span className={`dot ${o.progression}`}>{roleLabel[o.progression][0]}</span><span><b>{roleLabel[o.progression]}</b><small className="unitMeta">{o.unit_title} · {o.objective_id}</small><small>{o.objective}</small></span></button>)}</div>})}</div>
    </div>}
  </main>;
}
