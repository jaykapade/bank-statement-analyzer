"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type BudgetSlice = {
  name: string;
  value: number;
  color: string;
};

export function BudgetChart({ data }: { data: BudgetSlice[] }) {
  function formatValue(
    value: number | string | ReadonlyArray<number | string> | undefined,
    name: string | number | undefined,
  ): [string, string] {
    const amount = typeof value === "number" ? value : Number(value ?? 0);
    return [amount.toLocaleString(), String(name ?? "Category")];
  }

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={340}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="48%"
            dataKey="value"
            innerRadius={86}
            outerRadius={128}
            paddingAngle={4}
            stroke="rgba(9, 13, 22, 0.95)"
            strokeWidth={5}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "rgba(9, 13, 22, 0.92)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "18px",
              boxShadow: "0 20px 40px rgba(0,0,0,0.35)",
            }}
            formatter={formatValue}
            labelStyle={{ color: "white" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
