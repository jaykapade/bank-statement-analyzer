type RouteTableProps = {
  columns: string[];
  rows: Array<Record<string, string>>;
};

export function RouteTable({ columns, rows }: RouteTableProps) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10">
          <thead className="bg-black/10">
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/8">
            {rows.map((row, index) => (
              <tr key={index} className="bg-transparent">
                {columns.map((column) => (
                  <td
                    key={column}
                    className="px-4 py-4 text-sm leading-6 text-[var(--color-paper)]"
                  >
                    {row[column]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
