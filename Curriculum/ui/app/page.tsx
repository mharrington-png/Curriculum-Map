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
  { id: "M21", label: "Math 21", title: "Intermediate Algebra II", tone: "mint" },
  { id: "M22", label: "Math 22", title: "Geometry", tone: "gold" },
  { id: "M31", label: "Math 31", title: "Advanced Algebra", tone: "violet" },
  { id: "M32", label: "Math 32", title: "Trigonometry", tone: "coral" },
  { id: "M49", label: "Math 49", title: "Precalculus with Limits", tone: "navy" },
];
const roleLabel = { introduce: "Introduce", reinforce: "Reinforce", deepen: "Deepen", apply: "Apply" };

export default function Home() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [objectiveId, setObjectiveId] = useState<string | null>(null);
  const [skillId, setSkillId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [courseIndex, setCourseIndex] = useState(0);

  useEffect(() => { fetch(`${import.meta.env.BASE_URL}data/skill_progressions.json`).then(r => r.json()).then(setSkills); }, []);
  const allOccurrences = useMemo(() => skills.flatMap(s => s.occurrences), [skills]);
  const selectedCourse = courses.find(c => c.id === courseId);
  const courseOccurrences = allOccurrences.filter(o => o.course_id === courseId);
  const objectives = useMemo(() => {
    const map = new Map<string, Occurrence>();
    courseOccurrences.forEach(o => map.set(o.objective_id, o));
    return [...map.values()].sort((a, b) => a.objective_id.localeCompare(b.objective_id));
  }, [courseOccurrences]);
  const selectedObjective = objectives.find(o => o.objective_id === objectiveId);
  const objectiveSkills = skills.filter(s => s.occurrences.some(o => o.objective_id === objectiveId));
  const selectedSkill = skills.find(s => s.skill_id === skillId);
  const searchResults = query.length > 1 ? skills.filter(s => `${s.skill_id} ${s.description}`.toLowerCase().includes(query.toLowerCase())).slice(0, 8) : [];

  const openCourse = (id: string) => { setCourseId(id); setObjectiveId(null); setSkillId(null); };
  const goHome = () => { setCourseId(null); setObjectiveId(null); setSkillId(null); };
  const flipCourse = (direction: number) => setCourseIndex(current => (current + direction + courses.length) % courses.length);

  return <main>
    <header className="topbar">
      <button className="brand" onClick={goHome}><span className="brandmark">M</span><span>Middlesex Mathematics<small>Curriculum Map</small></span></button>
      <nav><button onClick={goHome}>Courses</button></nav>
      <div className="searchbox">
        <span>⌕</span><input aria-label="Search skills" placeholder="Search a skill…" value={query} onChange={e => setQuery(e.target.value)} />
        {searchResults.length > 0 && <div className="searchresults">{searchResults.map(s => <button key={s.skill_id} onClick={() => { setSkillId(s.skill_id); setQuery(""); }}>{s.description}<small>{s.skill_id}</small></button>)}</div>}
      </div>
    </header>

    {!courseId && !skillId && <div className="shell landing">
      <section className="hero"><p className="eyebrow">Department curriculum</p><h1>Choose a course.<br/><em>Follow the learning.</em></h1><p>Flip through the curriculum, then open a course to explore its topical units, learning objectives, and supporting skills.</p></section>
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
            <button className="opencourse" onClick={() => openCourse(c.id)} tabIndex={offset === 0 ? 0 : -1}>Open {c.label} <b>→</b></button>
          </article>;
        })}</div>
        <button className="flip next" onClick={() => flipCourse(1)} aria-label="Next course"><small>Next</small><span>→</span></button>
      </section>
      <div className="coursepicker" aria-label="Select a course">{courses.map((c, i) => <button className={i === courseIndex ? "active" : ""} key={c.id} onClick={() => setCourseIndex(i)} aria-label={`Show ${c.label}`}>{c.label}</button>)}</div>
      <p className="infinitehint">Keep flipping — the course sequence wraps around in either direction.</p>
    </div>}

    {courseId && selectedCourse && !skillId && <div className="shell page">
      <button className="back" onClick={goHome}>← All courses</button><div className="coursehead"><div><p className="eyebrow">{selectedCourse.label}</p><h1>{selectedCourse.title}</h1><p>{objectives.length} learning objectives · {new Set(courseOccurrences.map(o => o.skill_id)).size} supporting skills</p></div></div>
      <div className="coursebody"><section className="objectiveList">{["review","required","extension"].map(priority => {
        const group = objectives.filter(o => o.priority === priority); if (!group.length) return null;
        const units = [...new Map(group.map(o => [o.unit_id, { id: o.unit_id, title: o.unit_title }])).values()];
        return <div className="priorityGroup" key={priority}><div className="priorityHead"><h2 className={`priority ${priority}`}>{priority}</h2><span>{units.length} {units.length === 1 ? "unit" : "units"} · {group.length} objectives</span></div>{units.map(unit => {
          const unitObjectives = group.filter(o => o.unit_id === unit.id);
          return <details className="unit" key={unit.id}><summary><span><small>{priority} unit</small><b>{unit.title}</b></span><span className="unitCount">{unitObjectives.length} objectives</span><span className="chevron">⌄</span></summary><div className="unitObjectives">{unitObjectives.map(o => <button className={objectiveId === o.objective_id ? "objective active" : "objective"} key={o.objective_id} onClick={() => setObjectiveId(o.objective_id)}><small>{o.objective_id}</small><span>{o.objective}</span><b>→</b></button>)}</div></details>;
        })}</div>;
      })}</section>
      <aside className="detail">{selectedObjective ? <><p className="eyebrow">Objective detail</p><code>{selectedObjective.objective_id}</code><h2>{selectedObjective.objective}</h2><p className="muted">Supporting skills</p>{objectiveSkills.map(s => { const o=s.occurrences.find(x=>x.objective_id===objectiveId)!; return <button className="skillrow" key={s.skill_id} onClick={()=>setSkillId(s.skill_id)}><span className={`dot ${o.progression}`}>{roleLabel[o.progression][0]}</span><span>{s.description}<small>{roleLabel[o.progression]} · {o.relationship}</small></span><b>→</b></button>})}</> : <div className="empty"><span>↳</span><h2>Select an objective</h2><p>See its supporting skills and place in the curriculum progression.</p></div>}</aside></div>
    </div>}

    {selectedSkill && <div className="shell page"><button className="back" onClick={() => setSkillId(null)}>← {selectedCourse ? selectedCourse.label : "Back"}</button><p className="eyebrow">Skill explorer</p><code>{selectedSkill.skill_id}</code><h1 className="skilltitle">{selectedSkill.description}</h1><p className="lede">{selectedSkill.introduction_status === "inherited" ? selectedSkill.inherited_note : `First introduced in ${selectedSkill.first_introduced_course}.`} Once established, this skill remains available in the student toolkit.</p>
      <div className="timeline">{courses.map(c => { const items=selectedSkill.occurrences.filter(o=>o.course_id===c.id); const origin=selectedSkill.first_introduced_course; const originIndex=courses.findIndex(x=>x.label===origin); const currentIndex=courses.findIndex(x=>x.id===c.id); const carried=!items.length && (selectedSkill.introduction_status==="inherited" || (originIndex>=0 && currentIndex>originIndex)); return <div className={`timecourse ${items.length?"explicit":carried?"carried":"future"}`} key={c.id}><div className="timehead"><b>{c.label}</b>{carried&&<span>Carried forward</span>}</div>{items.map((o,i)=><button key={`${o.objective_id}-${i}`} onClick={()=>{setCourseId(o.course_id);setObjectiveId(o.objective_id);setSkillId(null)}}><span className={`dot ${o.progression}`}>{roleLabel[o.progression][0]}</span><span><b>{roleLabel[o.progression]}</b><small>{o.objective}</small></span></button>)}</div>})}</div>
    </div>}
  </main>;
}
