import { isAxiosError } from 'axios';

export function classificationErrorInfo(error: unknown) {
  const response = isAxiosError(error) ? error.response : undefined;
  const data = response?.data;
  const raw = data && typeof data === 'object' ? data.diagnostic : undefined;
  const diagnostic: Record<string, string | number> = {};
  if (raw && typeof raw === 'object') {
    for (const key of ['stage', 'code', 'model', 'platform', 'request_id', 'source_category', 'source_server', 'source_cf_ray']) {
      if (typeof raw[key] === 'string') diagnostic[key] = raw[key];
    }
    if (typeof raw.upstream_status === 'number') diagnostic.upstream_status = raw.upstream_status;
  }
  const title = ({ fetch: 'Não foi possível obter o enunciado', extract: 'Não foi possível extrair o enunciado',
    prepare: 'Não foi possível preparar a classificação', provider: 'A classificação pelo modelo não foi concluída',
    validation: 'Resposta da IA inválida' } as Record<string, string>)[diagnostic.stage] || 'Classificação não concluída';
  const message = typeof data?.detail === 'string' ? data.detail :
    response ? `O servidor respondeu HTTP ${response.status}, sem diagnóstico de classificação. Informe este erro para investigação.` :
    'Não foi possível comunicar com o servidor. Não há confirmação de classificação; evite repetir antes de conferir a conexão.';
  return { title, message, diagnostic,
    toastMessage: message + (diagnostic.request_id ? ` Código: ${diagnostic.request_id}` : '') };
}
