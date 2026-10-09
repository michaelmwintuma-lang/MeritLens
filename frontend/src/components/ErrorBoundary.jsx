// If a page breaks while drawing, show a message with a way out instead of a blank screen. The menu around the
// page keeps working, and moving to another page clears the error.
import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(previous) {
    // A different page (resetKey is the address) gets a fresh start
    if (this.state.error && previous.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="card" role="alert">
        <h1>Something went wrong on this page</h1>
        <p className="muted">Nothing was changed. Reload the page to try again, or go back to the overview.</p>
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>Reload the page</button>
          <a className="btn btn-plain" href="/">Go to the overview</a>
        </div>
      </div>
    );
  }
}
