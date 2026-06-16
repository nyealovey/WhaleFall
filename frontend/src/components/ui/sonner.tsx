import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  return <SonnerToaster closeButton position="top-right" richColors toastOptions={{ duration: 3500 }} {...props} />;
}

export { Toaster };
