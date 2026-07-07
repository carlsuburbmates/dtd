// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  courseSidebar: [
    {
      type: 'doc',
      id: 'start-here',
      label: 'Start Here',
    },
    {
      type: 'category',
      label: "Guide 1 — The Blueprint",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-blueprint/module-1-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-blueprint/module-1-lesson-1', label: "Section 1 — Build the Home Base" },
        { type: 'doc', id: 'modules/the-blueprint/module-1-lesson-2', label: "Section 2 — Remove Household Hazards" },
        { type: 'doc', id: 'modules/the-blueprint/module-1-lesson-3', label: "Section 3 — Prepare the First Vet Visit" },
        { type: 'doc', id: 'modules/the-blueprint/module-1-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 2 — The Transition Phase",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-transition-phase/module-2-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-transition-phase/module-2-lesson-1', label: "Section 1 — Accidents Need Routine, Not Anger" },
        { type: 'doc', id: 'modules/the-transition-phase/module-2-lesson-2', label: "Section 2 — Biting and Chewing Without Chaos" },
        { type: 'doc', id: 'modules/the-transition-phase/module-2-lesson-3', label: "Section 3 — Owner Overwhelm Is Data" },
        { type: 'doc', id: 'modules/the-transition-phase/module-2-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 3 — The Empathy Engine",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-lesson-1', label: "Section 1 — Read the Whole Dog" },
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-lesson-2', label: "Section 2 — Stress Signals Are Early Information" },
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-lesson-3', label: "Section 3 — Freeze, Growl, Snap: Do Not Punish the Warning" },
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-lesson-4', label: "Section 4 — Behaviour Change May Be Health Information" },
        { type: 'doc', id: 'modules/the-empathy-engine/module-3-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 4 — The Social Filter",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-social-filter/module-4-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-social-filter/module-4-lesson-1', label: "Section 1 — Socialisation Is Not Forced Interaction" },
        { type: 'doc', id: 'modules/the-social-filter/module-4-lesson-2', label: "Section 2 — Safe Early Exposure Before the World Gets Too Big" },
        { type: 'doc', id: 'modules/the-social-filter/module-4-lesson-3', label: "Section 3 — The Traffic-Light Rule for Fear" },
        { type: 'doc', id: 'modules/the-social-filter/module-4-lesson-4', label: "Section 4 — Handling, Grooming, and Vet Touch" },
        { type: 'doc', id: 'modules/the-social-filter/module-4-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 5 — The Sync Mechanics",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-lesson-1', label: "Section 1 — Reward the Moment You Want" },
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-lesson-2', label: "Section 2 — Stop Accidentally Paying for the Wrong Behaviour" },
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-lesson-3', label: "Section 3 — Calm Routines Before Big Feelings" },
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-lesson-4', label: "Section 4 — One Household, One Rule" },
        { type: 'doc', id: 'modules/the-sync-mechanics/module-5-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 6 — The Urban Flow & The Shield",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-lesson-1', label: "Section 1 — Public Stress: Make the Walk Smaller" },
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-lesson-2', label: "Section 2 — Street Hazards: The Shield" },
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-lesson-3', label: "Section 3 — Window Barking: Build the Shield" },
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-lesson-4', label: "Section 4 — Alone-Time Calm Without Punishing Distress" },
        { type: 'doc', id: 'modules/the-urban-flow-and-the-shield/module-6-tools', label: 'Checklists' },
      ],
    },
    {
      type: 'category',
      label: "Guide 7 — The Freedom Framework",
      collapsed: false,
      items: [
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-overview', label: 'Overview' },
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-lesson-1', label: "Section 1 — Freedom Expands Slowly" },
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-lesson-2', label: "Section 2 — Regression Is Information" },
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-lesson-3', label: "Section 3 — Signals and the Optional Toilet Bell" },
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-lesson-4', label: "Section 4 — Family Rules Make Freedom Clearer" },
        { type: 'doc', id: 'modules/the-freedom-framework/module-7-tools', label: 'Checklists' },
      ],
    },
  ],
};

export default sidebars;
