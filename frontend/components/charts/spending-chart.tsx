"use client";

import { useSyncExternalStore } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type CashflowPoint = {
  day: string;
  income: number;
  expenses: number;
};

export function SpendingChart({ data }: { data: CashflowPoint[] }) {
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  function formatValue(
    value: number | string | ReadonlyArray<number | string> | undefined,
    name: string | number | undefined,
  ): [string, string] {
    const amount = typeof value === "number" ? value : Number(value ?? 0);
    return [amount.toLocaleString(), name === "income" ? "Income" : "Expenses"];
  }

  return (
    <div className="h-full min-h-[420px] w-full">
      {!mounted ? (
        <div className="h-full min-h-[420px] w-full rounded-[1.5rem] border border-white/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))]" />
      ) : null}
      {mounted ? (
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={420}>
        <AreaChart data={data} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-emerald)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--color-emerald)" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-rose)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--color-rose)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="day"
            tick={{ fill: "var(--color-mist)", fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            tick={{ fill: "var(--color-mist)", fontSize: 12 }}
            tickFormatter={(value) => `${value / 1000}k`}
            tickLine={false}
            width={52}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(9, 13, 22, 0.92)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "18px",
              boxShadow: "0 20px 40px rgba(0,0,0,0.35)",
            }}
            cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
            formatter={formatValue}
            labelStyle={{ color: "white" }}
          />
          <Area
            dataKey="income"
            fill="url(#incomeFill)"
            stroke="var(--color-emerald)"
            strokeWidth={3}
            type="monotone"
          />
          <Area
            dataKey="expenses"
            fill="url(#expenseFill)"
            stroke="var(--color-rose)"
            strokeWidth={3}
            type="monotone"
          />
        </AreaChart>
      </ResponsiveContainer>
      ) : null}
    </div>
  );
}
