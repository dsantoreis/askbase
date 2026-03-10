import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const isGitHubPages = process.env.GITHUB_ACTIONS === 'true';

export default defineConfig({
  site: 'https://dsantoreis.github.io',
  base: isGitHubPages ? '/askbase/' : '/',
  integrations: [
    starlight({
      title: 'Askbase Docs',
      social: { github: 'https://github.com/dsantoreis/askbase' },
    }),
  ],
});
