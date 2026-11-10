/// <reference types="vite/client" />

declare module "@base-ui/react/button" {
  import * as React from "react";
  export namespace Button {
    export interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
      render?: React.ReactElement | ((props: any) => React.ReactElement);
    }
  }
  export const Button: React.ForwardRefExoticComponent<
    Button.Props & React.RefAttributes<HTMLButtonElement>
  >;
}

