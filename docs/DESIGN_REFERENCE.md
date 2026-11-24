# Frontend design reference

The supplied [SecureAuth repository](https://github.com/SyedMuzammil2028/secureauth-socket-system)
was cloned to a temporary directory outside this project. The inspected commit is
`fd7a18720137909df7ba82be433789b3af9078a8`.

Inspected: index.css, tailwind.config.ts, AdminShell.tsx, AdminDashboard.tsx,
AdminUsers.tsx, AdminLogs.tsx, Login.tsx, UserArea.tsx and button/input/table
components. This review used actual source, not just the README.

| Reference characteristic | Original implementation here |
| --- | --- |
| Neutral themes and indigo primary | Light background 0/0/100; dark 240/6/6; card 240/5/9; primary 234/55/58–60; readable muted text. |
| 280px / 76px sidebar | Persistent desktop collapse, role groups and accessible mobile drawer. |
| 64px top navigation | Breadcrumb, current workspace, theme switch and account summary. |
| Geist / Inter typography | Self-hosted Geist, compact headings, readable tables and forms. |
| Six-pixel corners and borders | Shared buttons, fields, panels, tables, badges and Radix dialogs. |
| Operational screens | Server-filtered/paginated tables, restrained metrics, clear dialogs. |
| Dark/light switch | Dark first, persistent light option; component and browser checks. |

No license was found in the reference. Source, assets, branding, authentication
and backend were not copied. General design principles and observed dimensions/
color values inform independently implemented components. No socket server,
external animation, MFA claim or decorative 3D background was added.

The client uses HttpOnly sessions and in-memory CSRF state, rather than the
reference's sessionStorage token pattern. Local storage holds only UI
preferences. Dependency/font license notices are in `docs/third-party`.
