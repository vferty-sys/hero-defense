// 왕국 수호자 — 설치한 앱의 오프라인 실행
// 처음 열 때 게임 파일(게임 화면·그림·아이콘)을 저장해 두고, 인터넷이 없으면 저장해 둔 것으로 실행합니다.
// - 게임 화면(index.html): 인터넷이 되면 항상 최신 버전을 받아서 실행 (안 되면 저장해 둔 것)
// - 그림 등 나머지: 저장해 둔 것을 바로 쓰고, 뒤에서 새 버전을 받아 다음 실행 때 반영
// 파일 구성이 크게 바뀌면 CACHE 이름의 숫자를 올리면 예전 저장본이 지워집니다.
const CACHE = 'kg-v1';
const CORE = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png',
              './icons/icon-maskable-512.png', './icons/apple-touch-icon.png', './icons/favicon-32.png'];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(CORE);
    try {                                                    // 게임용 그림 목록 (tools/prepare_images.py 가 만듦)
      const list = await (await fetch('./images/web/list.json', { cache: 'no-cache' })).json();
      await c.addAll([...list.sprites.map(n => `./images/web/${n}.png`), ...list.anims.map(n => `./images/web/${n}_anim.png`)]);
    } catch (_) {}
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  const page = req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('/index.html');
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    if (page) {                                              // 게임 화면: 최신 버전 먼저
      try {
        const res = await fetch(url.href, { cache: 'no-cache' });
        if (res.ok) { c.put('./index.html', res.clone()); return res; }
      } catch (_) {}
      return (await c.match('./index.html')) || Response.error();
    }
    const hit = await c.match(req, { ignoreSearch: true });  // 그림 등: 저장본 먼저, 뒤에서 새로 받기
    const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => null);
    if (hit) { e.waitUntil(net); return hit; }
    return (await net) || Response.error();
  })());
});
