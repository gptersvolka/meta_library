import React from "react";

const ErrorIcon = () => (
  <svg height="16" strokeLinejoin="round" viewBox="0 0 16 16" width="16">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M5.30761 1.5L1.5 5.30761L1.5 10.6924L5.30761 14.5H10.6924L14.5 10.6924V5.30761L10.6924 1.5H5.30761ZM5.10051 0C4.83529 0 4.58094 0.105357 4.3934 0.292893L0.292893 4.3934C0.105357 4.58094 0 4.83529 0 5.10051V10.8995C0 11.1647 0.105357 11.4191 0.292894 11.6066L4.3934 15.7071C4.58094 15.8946 4.83529 16 5.10051 16H10.8995C11.1647 16 11.4191 15.8946 11.6066 15.7071L15.7071 11.6066C15.8946 11.4191 16 11.1647 16 10.8995V5.10051C16 4.83529 15.8946 4.58093 15.7071 4.3934L11.6066 0.292893C11.4191 0.105357 11.1647 0 10.8995 0H5.10051ZM8.75 3.75V4.5V8L8.75 8.75H7.25V8V4.5V3.75H8.75ZM8 12C8.55229 12 9 11.5523 9 11C9 10.4477 8.55229 10 8 10C7.44772 10 7 10.4477 7 11C7 11.5523 7.44772 12 8 12Z"
    />
  </svg>
);

interface Error {
  message: string;
  action: string;
  link: string;
}

interface ErrorProps {
  error?: Error;
  label?: string;
  size?: "small" | "medium" | "large";
  children?: React.ReactNode;
}

export const Error = ({ error, label, size = "medium", children }: ErrorProps) => {
  return (
    <div
      className={`flex items-center gap-2 text-red-900 fill-red-900 font-sans
        ${{
          small: "text-[13px] leading-5",
          medium: "text-sm",
          large: "text-base"
        }[size]}`
      }
    >
      <ErrorIcon />
      {error ? (
        <>
          {error.message}
          <a
            className="font-medium flex items-center gap-0.5 -ml-1 hover:no-underline hover:opacity-60 duration-150"
            href={error.link}
            target="_blank"
          >
            {error.action}
          </a>
        </>
      ) : (
        <>
          {label && <span className="font-medium">{label}:</span>}
          {children}
        </>
      )}
    </div>
  );
};
