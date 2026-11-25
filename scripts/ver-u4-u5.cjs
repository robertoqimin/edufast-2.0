// U4 + U5 juntos no Edge (pedido do usuário): escola nova configurada pelo checklist (U4) e, na mesma
// escola, a tela única de Turmas, as telas migradas e Solicitações com filtro (U5).
// Uso: node scripts/ver-u4-u5.cjs [ritmo] [--passo] [--capturas DIR]   (recria a escola de gravação vazia)
process.argv.push('--com-u5');
require('./ver-u4.cjs');
