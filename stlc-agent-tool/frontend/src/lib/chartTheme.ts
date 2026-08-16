import { Chart as ChartJS, defaults } from 'chart.js';

// Base colors matching the Tailwind configuration
export const chartColors = {
  main: '#0D0F14',
  card: '#161922',
  elevated: '#1E2230',
  border: '#2A2F3E',
  textPrimary: '#E8EAF0',
  textSecondary: '#9AA1B5',
  primary: '#6C63FF',
  success: '#2ECC8F',
  fail: '#F0556A',
  warning: '#F0B94F',
  info: '#4FA8F0',
};

// Configure Chart.js global defaults for the entire application
export function applyChartTheme() {
  defaults.color = chartColors.textSecondary;
  defaults.font.family = "'Inter', sans-serif";
  
  if (defaults.plugins && defaults.plugins.legend) {
    defaults.plugins.legend.labels.color = chartColors.textPrimary;
  }
  
  if (defaults.plugins && defaults.plugins.tooltip) {
    defaults.plugins.tooltip.backgroundColor = chartColors.elevated;
    defaults.plugins.tooltip.titleColor = chartColors.textPrimary;
    defaults.plugins.tooltip.bodyColor = chartColors.textSecondary;
    defaults.plugins.tooltip.borderColor = chartColors.border;
    defaults.plugins.tooltip.borderWidth = 1;
    defaults.plugins.tooltip.padding = 12;
    defaults.plugins.tooltip.cornerRadius = 6;
  }
}
