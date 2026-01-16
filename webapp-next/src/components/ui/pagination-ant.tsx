"use client";

import React from "react";
import { Pagination, ConfigProvider } from "antd";

interface PaginationAntProps {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number, pageSize: number) => void;
  className?: string;
}

export const PaginationAnt: React.FC<PaginationAntProps> = ({
  current,
  total,
  pageSize,
  onChange,
  className,
}) => {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#3b82f6",
          borderRadius: 8,
        },
      }}
    >
      <div className={className}>
        <Pagination
          current={current}
          total={total}
          pageSize={pageSize}
          onChange={onChange}
          showSizeChanger={false}
          showQuickJumper
          showTotal={(total, range) =>
            `${range[0]}-${range[1]} / ${total}개`
          }
        />
      </div>
    </ConfigProvider>
  );
};

export default PaginationAnt;
