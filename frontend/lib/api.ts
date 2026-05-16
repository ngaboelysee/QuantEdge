export async function getTrade(pair: string, balance: number, risk: number) {
  const res = await fetch(
    `http://127.0.0.1:8000/trade?pair=${pair}&balance=${balance}&risk=${risk}`
  );

  if (!res.ok) {
    throw new Error("Backend request failed");
  }

  return res.json();
}