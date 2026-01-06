import { Component, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { switchMap, debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Subject } from 'rxjs';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnDestroy {
  symbol: string = 'RELIANCE';
  result: any = null;
  livePrice: string = '';
  loading = false;
  error = '';
  suggestions: any[] = [];
  showSuggestions = false;
  searchQuery = '';
  private pollSub?: Subscription;
  private searchSubject = new Subject<string>();

  constructor(private http: HttpClient) {
    // Setup search with debounce
    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(query => {
      if (query && query.length >= 1) {
        this.searchSymbols(query);
      } else {
        this.suggestions = [];
        this.showSuggestions = false;
      }
    });
  }

  analyze() {
    // Use searchQuery if symbol is not set, otherwise use symbol
    const symbolToAnalyze = this.symbol || this.searchQuery;
    if (!symbolToAnalyze) {
      this.error = 'Please enter a symbol';
      return;
    }
    
    this.symbol = symbolToAnalyze.toUpperCase();
    this.searchQuery = this.symbol;
    this.loading = true;
    this.error = '';
    this.result = null;

    this.http.get(`http://localhost:5000/analyze/${this.symbol}`).subscribe({
      next: (data: any) => {
        this.result = data;
        this.livePrice = data.currentPrice;
        this.loading = false;
        this.startLiveUpdates();
      },
      error: (err) => {
        this.error = 'Error: ' + (err.error?.error || err.message);
        this.loading = false;
      }
    });
  }

  private startLiveUpdates() {
    if (this.pollSub) this.pollSub.unsubscribe();
    this.pollSub = interval(5000).pipe(
      switchMap(() => this.http.get(`http://localhost:5000/live-price/${this.symbol}`))
    ).subscribe({
      next: (data: any) => this.livePrice = data.currentPrice,
      error: () => {}
    });
  }

  onSymbolInput(event: any) {
    const value = event.target.value;
    this.searchQuery = value;
    this.searchSubject.next(value);
  }

  searchSymbols(query: string) {
    this.http.get(`http://localhost:5000/search-symbols?q=${encodeURIComponent(query)}&limit=10`).subscribe({
      next: (data: any) => {
        this.suggestions = data.symbols || [];
        this.showSuggestions = this.suggestions.length > 0;
      },
      error: () => {
        this.suggestions = [];
        this.showSuggestions = false;
      }
    });
  }

  selectSymbol(suggestion: any) {
    this.symbol = suggestion.symbol;
    this.searchQuery = suggestion.symbol;
    this.suggestions = [];
    this.showSuggestions = false;
    // Trigger analyze automatically when symbol is selected
    if (this.symbol) {
      this.analyze();
    }
  }

  onInputFocus() {
    if (this.suggestions.length > 0) {
      this.showSuggestions = true;
    }
  }

  onInputBlur() {
    // Delay to allow click on suggestion
    setTimeout(() => {
      this.showSuggestions = false;
    }, 200);
  }

  ngOnDestroy() {
    if (this.pollSub) this.pollSub.unsubscribe();
    this.searchSubject.complete();
  }
}
