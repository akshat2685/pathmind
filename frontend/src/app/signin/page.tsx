import { redirect } from "next/navigation";

/**
 * /signin is retired: the unified app has ONE sign-in page (/login, the
 * living-sketchbook design). This route stays as a redirect so old links
 * and bookmarks keep working.
 */
export default function SignInRedirect() {
  redirect("/login");
}
