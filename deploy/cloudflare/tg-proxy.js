// Бесплатный прокси к Telegram на Cloudflare Workers.
// /bot<токен>/<метод> → api.telegram.org, /s/<канал> → t.me
export default {
  async fetch(request) {
    const url = new URL(request.url)
    let target
    if (url.pathname.startsWith('/bot')) target = 'https://api.telegram.org'
    else if (url.pathname.startsWith('/s/')) target = 'https://t.me'
    else return new Response('ok', { status: 200 })
    const upstream = new Request(target + url.pathname + url.search, {
      method: request.method,
      headers: { 'content-type': request.headers.get('content-type') || 'application/json',
                 'user-agent': 'Mozilla/5.0 (compatible; KodverkBot/1.0)' },
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
      redirect: 'manual',
    })
    return fetch(upstream)
  },
}
