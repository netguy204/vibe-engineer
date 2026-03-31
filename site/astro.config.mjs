import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://veng.dev',
  output: 'static',
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
    },
  },
});
