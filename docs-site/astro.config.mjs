import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
export default defineConfig({ integrations: [starlight({ title: 'Askbase Docs', social:{ github:'https://github.com/dsantoreis/askbase' } })] });
