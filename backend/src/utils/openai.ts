import { OpenAI } from "openai";
import dotenv from "dotenv";

dotenv.config();

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

export async function summarizeMetric(metric: string, data: [number, number][]) {
  const tableData = data.map(([year, value]) => `${year}: ${value}`).join("\n");

  const prompt = `
You are a financial analyst AI. Write a 2-3 sentence overview about this 10-year financial trend for: "${metric}".

Data:
${tableData}

Avoid unnecessary commentary. Focus on what the numbers show.
`;

  const chatResponse = await openai.chat.completions.create({
    model: "gpt-4o",
    temperature: 0.4,
    messages: [{ role: "user", content: prompt }],
  });

  return chatResponse.choices[0].message.content?.trim() || "";
}
