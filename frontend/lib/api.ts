export async function getTrade(pair: string, balance: number, risk: number) {
  const res = await fetch(
    `https://myapp-mtzb.onrender.com/trade?pair=${pair}&balance=${balance}&risk=${risk}`
  );

  if (!res.ok) {
    throw new Error("Backend request failed");
  }

  return res.json();
}
